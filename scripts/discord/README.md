# Test


Stop server
Run with : python3 discord_bot.py

# Installation on the server

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies with pinned versions
pip install -r requirements.txt

# Run the bot
python3 discord_bot.py
```

## Notes for the server
- Ensure the file `/config/token.txt` exists and contains the bot token
- The bot uses discord.py 1.7.3 (stable) and pinned dependency versions
- If you have time issues on WSL: `sudo hwclock -s`
- For time synchronization on the server:
    ```bash
    sudo service ntp stop
    sudo ntpdate pool.ntp.org
    sudo service ntp start
    sudo hwclock --systohc
    ```
