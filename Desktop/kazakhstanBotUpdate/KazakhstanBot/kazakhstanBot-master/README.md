## Setting Up Task Scheduler

To ensure the bot runs continuously, you can set up a task in Task Scheduler:

1. **Open Task Scheduler:**
   - Press `Win + R`, type `taskschd.msc`, and press `Enter`.

2. **Create a New Task:**
   - In the Actions pane, click on `Create Task`.

   **General Settings:**
   - Name the task `KazakhstanBot`.
   - Select `Run whether user is logged on or not`.
   - Check `Run with highest privileges`.

3. **Triggers:**
   - Go to the `Triggers` tab and click `New`.
   - Set the task to begin `At startup`.
   - Click `OK`.

4. **Actions:**
   - Go to the `Actions` tab and click `New`.
   - Set `Action` to `Start a program`.
   - Browse and select your `start_bot.bat` file.
   - Click `OK`.

5. **Conditions:**
   - Go to the `Conditions` tab.
   - Uncheck `Start the task only if the computer is on AC power`.

6. **Settings:**
   - Go to the `Settings` tab.
   - Ensure `Allow task to be run on demand` is checked.
   - Check `If the task fails, restart every`, and set a suitable time interval (e.g., 1 minute).
   - Set the `Attempt to restart up to` field to a reasonable number (e.g., 3).

7. **Save and Start the Task:**
   - Click `OK` to save the task.
   - When prompted, enter the password for the user account under which the task will run.
   - You can manually test the task by right-clicking on it in Task Scheduler and selecting `Run`.
