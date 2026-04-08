# 🌻 SnapHAT - Python-based app for Raspberry Pi handheld camera

This repository contains software for **SnapHAT** - a RaspberryPi-based photo camera addon board (see: [SnapHAT PCB](https://github.com/marchmare/snaphat-pcb)).

SnapHAT is a RaspberryPi-based handheld camera device with real-time Bayer ordered dithering, custom pixel-art and sprite-based UI and classic console-inspired controls.

> [!TIP] This repository is work in progress — core features are functional, but the PCB for this device is still evolving so mapping and configuration might not be definitive yet.

## Features

* Real-time dithered camera preview with adjustable parameters and switchable color palettes, using `Picamera2` for camera capture and `OpenCV` for dithering
* Dithered frame capture to SD card at 320x240 resolution
* Direct framebuffer rendering with no desktop environment required
* Custom UI system built from pixelart spritesheets, featuring modular components such as battery indicators, text blocks and popups
* Tact switch navigation inspired by early handheld devices
* Buzzer-based audio feedback using a custom sound generator 
* Sensor integration for battery monitoring and orientation tracking (INA219, LIS2DW12)

## Getting started

### Requirements

* Raspberry Pi OS Lite 64 bit (tested on 64-bit, Debian 13 "Trixie")
* Python 3.13
* I2C and SPI enabled via `raspi-config`

Scripts in this repository assume hardware from [SnapHAT PCB](https://github.com/
marchmare/snaphat-pcb) is used, follow the link for details.

### Installation

1. Follow the instructions from the [RaspberryPi configuration](#raspberrypi-configuration) to properly setup `config.txt` and `cmdline.txt` files.

2. Clone the repository:

        git clone https://github.com/marchmare/snaphat-.git
        cd snaphat-

3. Run the entry script:

        python3 main.py

Captured frames are saved into `camera/` directory.

### Controls

| Button name | RPi BCM pin | Camera preview function | Gallery function |
| ----------- | ----------- | ------------ | ------------ | 
| A           | 27          | Toggle color palette | --- | 
| MENU        | 17          | Open photo gallery | --- | 
| B           | 22          | --- | Back to camera | 
| UP          | 19          | Increase color levels | --- | 
| DOWN        | 5           | Decrease color levels | --- | 
| LEFT        | 6           | Decrease Bayer matrix size | Next photo | 
| RIGHT       | 13          | Increase Bayer matrix size | Previous photo | 
| SHUTTER     | 26          | Capture photo | --- | 

## Project structure
        .
        ├── assets/             - PNG spritesheets used by UI
        ├── camera/             - output directory for captured images
        ├── core/               - core logic and settings 
        ├── device/             - hardware drivers
        ├── sound/              - sound generation modules
        ├── ui/                 - UI framework
        ├── main.py             - entry point script
        ├── snaphat.service     - systemd auto-start service 
        └── README.md       

## App configuration - `core/settings.py`

Some behaviour can be customized via [settings.py](core/settings.py) file. This includes input and output mappings, assets and output directories paths, target display resolution etc.

## RaspberryPi configuration 

### `raspi-config`

Run:

        sudo raspi-config

Enable:

    * I2C
    * SPI

### `config.txt`

Configure GPIO pullups for buttons:

        # GPIOs
        gpio=17,27,22,5,6,13,19,26=pu

Configure SPI LCD overlay:

        # SPI LCD
        dtoverlay=fbtft,spi0-0,ili9341,bgr,rotate=270,cs=0,dc_pin=25,reset_pin=24,bl_pin=12

### `cmdline.txt`

> [!WARNING]
> Create backup before modifying `cmdline.txt`.

Enable silent boot with no console, enable OTG mode on RPi and speed up booting time (replace <partuid> and <reg> with values specific to your device):

```
root=PARTUUID=<partuid> rootfstype=ext4 rootwait modules-load=dwc2,g_mass_storage quiet loglevel=0 logo.nologo vt.global_cursor_default=0 splash fastboot fsck.mode=skip cfg80211.ieee80211_regdom=<reg>
```

To find PARTUUID:

        grep ext4 /etc/fstab | grep -oP 'PARTUUID=\K[^ ]+'

`<reg>` is your Wi-Fi regulatory domain.

### Auto-start on boot 

1. Update paths to SnapHAT scripts repository and username if they differ from the default in `snaphat.service` file:

        User=pi 
        WorkingDirectory=/home/pi/snaphat 
        ExecStart=/usr/bin/python3 /home/pi/snaphat-sw/main.py  

2. Copy the service file:

        sudo cp snaphat.service /etc/systemd/system/

3. Reload `systemd`:

        sudo systemctl daemon-reexec
        sudo systemctl daemon-reload

4. Enable the service:

        sudo systemctl enable snaphat.service

5. Reboot your RPi

        sudo reboot

## Future goals

* On-device settings menu
* Gallery tools (delete, palette swap for saved images)
* Improved UI framework (scrolling screens, context menus, richer text blocks)
* USB mass-storage mode via OTG
