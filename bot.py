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

import os
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.environ['DISCORD_BOT_TOKEN']
AUTHORIZED_USER_IDS = os.environ.get('AUTHORIZED_USER_ID', '').split(',')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Convert AUTHORIZED_USER_IDS to a set of integers
WHITELIST = set(map(int, filter(str.isdigit, AUTHORIZED_USER_IDS)))

def is_user_whitelisted(user_id: int) -> bool:
    return user_id in WHITELIST

def split_message(message: str, max_length: int = 2000) -> list:
    """Split a message into parts that don't exceed the max_length."""
    return [message[i:i+max_length] for i in range(0, len(message), max_length)]

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.tree.command(name="start", description="Start using Ewok")
async def start(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if is_user_whitelisted(user_id):
        embed = discord.Embed(title="Welcome to Ewok!", description="Please choose an option or wait for notifications from the extension:", color=discord.Color.blue())
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="🆔 Show User ID", custom_id="show_user_id"))
        view.add_item(discord.ui.Button(label="📖 Instructions", custom_id="instructions"))
        view.add_item(discord.ui.Button(label="📥 Download Extension", custom_id="download_extension"))
        
        await interaction.response.send_message(embed=embed, view=view)
    else:
        embed = discord.Embed(title="Access Restricted", description=f"Your user ID is not whitelisted. Please contact the server admin and provide them with your user ID: `{user_id}`", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data['custom_id']
        
        if custom_id == "show_user_id":
            user_id = interaction.user.id
            await interaction.response.send_message(f"This is your user ID: `{user_id}`\nCopy it into the Ewok and Ewok Extension settings to start receiving task notifications.", ephemeral=True)
        
        elif custom_id == "instructions":
            instructions_text = """
            **📖 Instructions for using Ewok**

            Please follow the steps below to use Ewok and the extension:

            1. 🆔 **Take Note of Your User ID**
               - Make sure to take note of your user ID. You will need it to log in to Ewok and insert it in the Ewok settings page.

            2. 💻 **Download Ewok Chrome extension**
               - Extract the files from the compressed archive into a convenient folder.
               - Use an unzip utility, such as 7-Zip on Windows or The Unarchiver on macOS, or right-click and select 'Extract All'.
               - Delete the .zip file after extracting the files.
               - Remember to keep the extension folder. Removing it will cause the extension to stop working after the next browser restart, and you'll need to reinstall it.

            3. 🛠️ **Install Ewok Chrome extension**
               - Open your browser and go to the 'Extensions' page.
               - Enable 'Developer mode' in the top right corner.
               - Click 'Load unpacked' and select the folder containing the extracted Ewok files.
               - The extension should now be installed and ready to use.

            4. 💡 **Download Ewok Extension**
               - Download Ewok Extension
               - Follow the same extraction and installation steps as before to set up the Ewok extension.

            5. 🚪 **Log in to Ewok**
               - Enter your user ID to log in to Ewok.
               - Open the Ewoq home page in your browser.
               - Keep the Ewoq home page open so that the bot can check for notifications and send them to your Discord.

            6. ⚙️ **Configure Ewok Extension**
               - Open the Ewok extension settings page.
               - Enter your user ID in the settings to enable automatic reporting to the bot.

            7. 📝 **Track Tasks and Generate Reports**
               - Work on your tasks as usual.
               - When you're finished, open the Ewok extension.
               - Click the 'Send Report to Bot' button to receive Welocalize-recognized time for your work.

            Enjoy using Ewok! 😊🚀
            """
            message_parts = split_message(instructions_text)
            await interaction.response.send_message(message_parts[0], ephemeral=True)
            for part in message_parts[1:]:
                await interaction.followup.send(part, ephemeral=True)
        
        elif custom_id == "download_extension":
            extensions_text = """
            You can download the extensions from the following links:

            1. 📥 [Download Ewok](insert-url)

            Click on the links to download the extensions and proceed with the installation.
            """
            await interaction.response.send_message(extensions_text, ephemeral=True)

bot.run(TOKEN)
