"""
Ewokd: a bot that tracks tasks, alerts you instantly, and calculates your EWOQ earnings.
Copyright (C) 2023-2025 Marco Cipriani marcocipriani@tutanota.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ValidationError, validator
import logging
import pandas as pd
import os
import httpx
import datetime
import json

AUTHORIZED_USER_IDS = os.environ.get('AUTHORIZED_USER_ID', '').split(',')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.middleware("http")
async def add_payload_to_state(request: Request, call_next):
    if request.method == "POST":
        body = await request.body()
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = None
        request.state.payload = payload
    response = await call_next(request)
    return response


class Message(BaseModel):
    text: str = Field(..., max_length=120)
    count: Optional[int] = 1

    @validator('count')
    def count_in_range(cls, v):
        if not 1 <= v <= 9:
            raise ValueError('count must be between 1 and 9')
        return v

class StatusPayload(BaseModel):
    user_id: int
    
DISCORD_API_BASE = 'https://discord.com/api/v10'

class SignalPayload(BaseModel):
    user_id: int
    messages: List[Message]

    @validator('messages')
    def messages_length(cls, v):
        if not len(v) <= 2:
            raise ValueError('You must provide 1 or 2 messages')
        return v

class Task(BaseModel):
    dates: Dict[str, int]
    taskCount: int
    time: int
    
    def __getitem__(self, item):
        return getattr(self, item)
    
class TaskPayload(BaseModel):
    user_id: int
    tasks: Dict[str, Task]

    @validator('tasks')
    def tasks_values(cls, v):
        for task_name, task_info in v.items():
            if task_info.taskCount <= 0 or task_info.time <= 0:
                raise ValueError('Task count and time must be positive')
        return v

WHITELIST = set(map(int, filter(str.isdigit, AUTHORIZED_USER_IDS)))

def is_user_whitelisted(user_id: int) -> bool:
    return user_id in WHITELIST

@app.post('/status')
async def status(request: Request):
    try:
        payload = StatusPayload(**request.state.payload)
        user_id = payload.user_id
        
        if not is_user_whitelisted(user_id):
            return JSONResponse({'error': 'User not whitelisted'}, status_code=403)

        return JSONResponse({'status': 'Online'}, status_code=200)
    except ValueError:
        return JSONResponse({'error': 'Invalid user ID'}, status_code=400)

@app.post('/login')
async def login(request: Request):
    try:
        payload = StatusPayload(**request.state.payload)
        user_id = payload.user_id
        
        if is_user_whitelisted(user_id):
            return JSONResponse({'message': 'Login successful'}, status_code=200)
        else:
            return JSONResponse({'error': 'User not allowed'}, status_code=403)
    except ValueError:
        return JSONResponse({'error': 'Invalid user ID'}, status_code=400)

@app.post('/send_signal')
async def send_signal(request: Request):
    try:
        payload = SignalPayload(**request.state.payload)
        user_id = payload.user_id
        messages = payload.messages

        if not is_user_whitelisted(user_id):
            return JSONResponse({'error': 'User not whitelisted'}, status_code=403)

        try:
            async with httpx.AsyncClient() as client:
                # Create a DM channel
                create_dm_response = await client.post(
                    f'{DISCORD_API_BASE}/users/@me/channels',
                    json={'recipient_id': str(user_id)},
                    headers={'Authorization': f'Bot {os.environ["DISCORD_BOT_TOKEN"]}'}
                )
                create_dm_response.raise_for_status()
                dm_channel = create_dm_response.json()
                
                # Send messages to the DM channel
                for message in messages:
                    for _ in range(message.count):
                        response = await client.post(
                            f'{DISCORD_API_BASE}/channels/{dm_channel["id"]}/messages',
                            json={'content': message.text},
                            headers={'Authorization': f'Bot {os.environ["DISCORD_BOT_TOKEN"]}'}
                        )
                        response.raise_for_status()
                
                return JSONResponse({'message': 'Signal sent to the Discord user successfully'}, status_code=200)
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error sending signal to Discord: {str(e)}", exc_info=True)
            return JSONResponse({'error': f'Error sending signal to Discord: {str(e)}'}, status_code=e.response.status_code)
        except Exception as e:
            logging.error(f"Unexpected error in send_signal: {str(e)}", exc_info=True)
            return JSONResponse({'error': f'Unexpected error: {str(e)}'}, status_code=500)
    except ValidationError as e:
        logging.error(f"Validation error in send_signal: {str(e)}", exc_info=True)
        return JSONResponse({'error': f'Invalid payload: {str(e)}'}, status_code=400)

def format_seconds(seconds):
    """Convert seconds into 'X hour(s) Y minute(s)' format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f'{hours} hour(s) {minutes} minute(s)'

def load_or_create_tasks_df():
    """Load the tasks CSV or create a new DataFrame with proper columns."""
    try:
        df = pd.read_csv('tasks.csv')
        # Ensure all required columns exist
        required_columns = ['Task Name', 'RPH', 'default_rate']
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        return df
    except (pd.errors.EmptyDataError, FileNotFoundError):
        # Create new DataFrame with proper structure
        return pd.DataFrame(columns=['Task Name', 'RPH', 'default_rate'])

def get_task_rate(df, task_name):
    """Get task rate from DataFrame, handling missing columns gracefully."""
    if task_name in df['Task Name'].values:
        # Check if default_rate column exists and has a value
        if 'default_rate' in df.columns:
            rate_series = df.loc[df['Task Name'] == task_name, 'default_rate']
            if not rate_series.empty:
                rate = rate_series.values[0]
                if pd.notna(rate):
                    return rate, False
    # If task is not found or default_rate is not available, use fallback
    return 0.118, True
    
@app.post('/process_tasks')
async def process_tasks(request: Request):
    payload = TaskPayload(**request.state.payload)
    user_id = payload.user_id

    if not user_id:
        return JSONResponse({'error': 'Chat ID is required'}, 400)

    if not is_user_whitelisted(user_id):
        return JSONResponse({'error': 'User not whitelisted'}, 403)

    df = load_or_create_tasks_df()

    total_task_count = 0
    total_time = 0
    total_payout = 0
    task_count_by_rate = {}
    new_tasks = []
    response_msg = ''

    all_dates = []

    for task_name, task_info in payload.tasks.items():
        task_dates = [datetime.datetime.strptime(d, "%Y-%m-%d") for d in task_info['dates'].keys()]
        all_dates.extend(task_dates)

        taskCount = task_info.taskCount
        total_task_count += taskCount

        task_rate, is_new = get_task_rate(df, task_name)
        
        if is_new:
            new_tasks.append(task_name)
            # Use pd.concat instead of deprecated append
            new_row = pd.DataFrame({'Task Name': [task_name], 'RPH': [25], 'default_rate': [task_rate]})
            df = pd.concat([df, new_row], ignore_index=True)

        # Get RPH value
        if task_name in df['Task Name'].values:
            rph_series = df.loc[df['Task Name'] == task_name, 'RPH']
            rph = rph_series.values[0] if not rph_series.empty and pd.notna(rph_series.values[0]) else 25
        else:
            rph = 25

        task_count_by_rate[task_rate] = task_count_by_rate.get(task_rate, 0) + taskCount

        task_time = int(taskCount * rph)
        total_time += task_time

        task_payout = taskCount * task_rate
        total_payout += task_payout

        response_msg += (
            f'🔧 Task: **{task_name}**, Dates: {", ".join([d.strftime("%d %b %Y") for d in task_dates])}, '
            f'Tasks completed: {taskCount}, Fixed RPH: {rph:.2f} seconds, '
            f'Task rate: ${task_rate:.3f},\n'
            f'⏰ Total time for this task: {format_seconds(task_time)},\n'
            f'💰 Estimated Payout: ${task_payout:.2f}.\n\n'
        )

    if all_dates:
        response_msg = (
            f"🗓️ Report Date Range: {min(all_dates).strftime('%d %b %Y')} - {max(all_dates).strftime('%d %b %Y')}\n\n"
            + response_msg
        )

        for rate, count in task_count_by_rate.items():
            response_msg += f'📝 Total tasks completed at ${rate:.3f}: **{count}**\n'

        response_msg += f"📝 Total tasks completed: **{total_task_count}**\n"
        response_msg += f"⏱️ Total time spent: **{format_seconds(total_time)}**.\n"
        response_msg += f"💰 Estimated total payout: **${total_payout:.2f}**.\n"

    if new_tasks:
        df.to_csv('tasks.csv', index=False)
        response_msg += (
            "🆕 New tasks detected. Please update the time per task and task rate in 'tasks.csv': "
            + ', '.join(f"**{task_name}**" for task_name in new_tasks)
        )
        response_msg += "\n✅ A placeholder time per task of 25 seconds and task rate of $0.118 has been added.\n"

    response_parts = [response_msg[i:i+2000] for i in range(0, len(response_msg), 2000)]

    try:
        async with httpx.AsyncClient() as client:
            # Create a DM channel
            create_dm_response = await client.post(
                f'{DISCORD_API_BASE}/users/@me/channels',
                json={'recipient_id': str(user_id)},
                headers={'Authorization': f'Bot {os.environ["DISCORD_BOT_TOKEN"]}'}
            )
            create_dm_response.raise_for_status()
            dm_channel = create_dm_response.json()
            
            # Send messages to the DM channel
            for part in response_parts:
                response = await client.post(
                    f'{DISCORD_API_BASE}/channels/{dm_channel["id"]}/messages',
                    json={'content': part},
                    headers={'Authorization': f'Bot {os.environ["DISCORD_BOT_TOKEN"]}'}
                )
                response.raise_for_status()
            
        return JSONResponse({
            'message': 'Processed tasks and sent report to Discord successfully',
            'total_time': format_seconds(total_time),
            'total_payout': f"${total_payout:.2f}"
        }, status_code=200)
    except httpx.HTTPStatusError as e:
        logging.error(f"HTTP error sending report to Discord: {str(e)}", exc_info=True)
        return JSONResponse({'error': f'Error sending report to Discord: {str(e)}'}, status_code=e.response.status_code)
    except Exception as e:
        logging.error(f"Unexpected error in process_tasks: {str(e)}", exc_info=True)
        return JSONResponse({'error': f'Unexpected error: {str(e)}'}, status_code=500)

@app.post('/get_task_stats')
async def process_tasks_no_report(request: Request):
    payload = TaskPayload(**request.state.payload)
    user_id = payload.user_id

    if not user_id:
        return JSONResponse({'error': 'User ID is required'}, 400)

    if not is_user_whitelisted(user_id):
        return JSONResponse({'error': 'User not whitelisted'}, 403)

    df = load_or_create_tasks_df()

    total_task_count = 0
    total_time = 0
    total_payout = 0
    new_tasks = []

    for task_name, task_info in payload.tasks.items():
        taskCount = task_info.taskCount
        total_task_count += taskCount

        task_rate, is_new = get_task_rate(df, task_name)
        
        if is_new:
            new_tasks.append(task_name)
            # Use pd.concat instead of deprecated append
            new_row = pd.DataFrame({'Task Name': [task_name], 'RPH': [25], 'default_rate': [task_rate]})
            df = pd.concat([df, new_row], ignore_index=True)

        # Get RPH value
        if task_name in df['Task Name'].values:
            rph_series = df.loc[df['Task Name'] == task_name, 'RPH']
            rph = rph_series.values[0] if not rph_series.empty and pd.notna(rph_series.values[0]) else 25
        else:
            rph = 25

        task_time = int(taskCount * rph)
        total_time += task_time

        task_payout = taskCount * task_rate
        total_payout += task_payout

    if new_tasks:
        df.to_csv('tasks.csv', index=False)

    return JSONResponse({
        'message': 'Processed tasks successfully', 
        'total_time': format_seconds(total_time), 
        'total_payout': f"${total_payout:.2f}"
    }, 200)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)