# Ewokd-Discord

**Ewokd** is a bot that tracks tasks, notifies you when they’re available, estimates your EWOQ earnings, and calculates the time spent working based on each task's RPH (rate per hour).

---

## Features

- 📢 Sends notifications when tasks are available  
- ✅ Tracks completed tasks  
- 💰 Estimates earnings for EWOQ  
- 🔧 Extensible — you can script your own functionality  

---

## Requirements

- Python **3.9 - 3.13.7**  
- Discord account & bot token  
- `pip` (Python package manager)  

---

## Installation

1. **Clone the repository**  

```bash
git clone https://codeberg.org/mcipriani/ewokd-ds.git
```

  or

```bash
git clone https://github.com/marcocipriani1/ewokd-ds.git
```

```bash
cd ewoq-ds
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure your bot**  

- Add your Discord bot token to a `.env` file or configuration file as required by the code.
- Add your Discord user ID and the server port.  
- An `.env-example` file is provided to guide you.

---

## Running Ewokd

Ewokd uses a **Procfile** to manage multiple processes, allowing you to run both the web server and the bot worker concurrently.

> You will need to create a `task.csv` file in the root folder of the server and populate it yourself according to the example provided in `task_example.csv`.

Then run:

```bash
honcho start
```

- Honcho will start both processes and prefix logs (`web | ...`, `worker | ...`) for clarity.

- You can stop both processes at any time with `Ctrl+C`.

### Running Ewokd as a Systemd Service

Ewokd comes with a `systemd` unit file, so you can run it as a service that starts on boot and restarts automatically.

⚠️ **Warning:** The included systemd unit file points to `/root/ewokd-ds` by default. Modify the paths in the unit file to match your installation directory.

#### Instructions

1. Copy the included systemd unit file to the system directory:

```bash
cp ewokd.service /etc/systemd/system/
```

2. Reload systemd to recognize the new service:

```bash
systemctl daemon-reload
```

3. Start Ewokd:

```bash
systemctl start ewokd.service
```

4. Enable it to start automatically on boot:

```bash
systemctl start ewokd.service
```

5. Check the status or view live logs:

```bash
systemctl status ewokd.service
journalctl -u ewokd.service -f
```

## Development Notes

- The code is actively being revised — expect breaking changes.
- You are encouraged to create your own scripts or extensions.
- Future official extensions will not prevent you from maintaining custom scripts.

---

---

## License

    Ewokd: a bot that tracks tasks, alerts you instantly, and calculates your EWOQ earnings. 
    Copyright (C) 2023-2025  Marco Cipriani marcocipriani@tutanota.com

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

---
