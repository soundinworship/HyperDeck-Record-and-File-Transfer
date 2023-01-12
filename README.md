# HyperDeck-Record-and-File-Transfer
Controls a local HyperDeck, and allows the user to transfer its video files to a local computer.

This repository is built using Python 3.11 and requires the aiohttp module.

Edit the [locals.json](https://github.com/soundinworship/HyperDeck-Record-and-File-Transfer/blob/main/Blackmagic%20HyperDeck%20Protocol/WebUI/Resources/local.json) file with the ip address of your HyperDeck Studio device and the local download folder path to transfer the video files from the Hyperdeck to a specific local path via FTP.

You can use the web browser interfact to adjust settings such as "Auto Record on Startup" or "Auto Download on Stop", or you can edit those boolean values in [settings.json](https://github.com/soundinworship/HyperDeck-Record-and-File-Transfer/blob/main/Blackmagic%20HyperDeck%20Protocol/WebUI/Resources/settings.json).

This project does not yet include every HyperDeck command possible, but I would love for this project to grow to fit more use cases.

Feel free to reach out if you would like to enhance make this project.
