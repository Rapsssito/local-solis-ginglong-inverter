# Local Solis/Ginglong Inverter Logger via LAN for Home Assistant<!-- omit in toc -->

## Table of Contents<!-- omit in toc -->
- [Installation](#installation)
- [Getting started](#getting-started)
- [Tested devices](#tested-devices)
- [Acknowledgements](#acknowledgements)


## Installation

The easiest way, if you are using [HACS](https://hacs.xyz/), is to install through HACS.

For manual installation, copy all the folders inside `custom_components/` and all of its contents into your Home Assistant's `custom_components` folder. This folder is usually inside your `/config` folder. If you are running Hass.io, use SAMBA to copy the folder over. If you are running Home Assistant Supervised, the `custom_components` folder might be located at `/usr/share/hassio/homeassistant`. You may need to create the `custom_components` folder and then copy the folders inside. After copying the folders, restart Home Assistant. You should see the integration in the integrations page.

## Getting started

## Tested devices

| Device              | Firmware version | Tested |
| ------------------- | ---------------- | ------ |
| S5-GR1P(0.7-3.6)K-M | v1.0             | ✅      |


## Acknowledgements

This would not be possible without the great work published by [@planetmarshall](https://github.com/planetmarshall/solis-service) for reverse engineering the protocol ([link to the blog post](https://www.algodynamic.co.uk/reverse-engineering-the-solisginlong-inverter-protocol.html)).
