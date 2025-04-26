# Local Solis/Ginglong Inverter Logger via LAN for Home Assistant<!-- omit in toc -->

Home Assistant integration for Solis/Ginglong inverters using the Wi-Fi datalogger. This integration creates a fake Solis server that listens to the datalogger's requests and responds accordingly, serving as a "machine in the middle attack" to intercept the data. The server is then able to send the data to Home Assistant. This enables the use of the Solis/Ginglong inverter without the need for an outbound connection to the internet. The integration is based on the work of [@planetmarshall](https://github.com/planetmarshall/solis-service).

_In the future, it would be great to add support optionally sending the data to the Solis cloud, so that you can use the Solis app and Home Assistant at the same time. If you are interested in this feature, please open a pull request._

## Table of Contents<!-- omit in toc -->
- [Installation](#installation)
- [Getting started](#getting-started)
- [Tested devices](#tested-devices)
- [Acknowledgements](#acknowledgements)


## Installation

The easiest way, if you are using [HACS](https://hacs.xyz/), is to install through HACS.

For manual installation, copy all the folders inside `custom_components/` and all of its contents into your Home Assistant's `custom_components` folder. This folder is usually inside your `/config` folder. If you are running Hass.io, use SAMBA to copy the folder over. If you are running Home Assistant Supervised, the `custom_components` folder might be located at `/usr/share/hassio/homeassistant`. You may need to create the `custom_components` folder and then copy the folders inside. After copying the folders, restart Home Assistant. You should see the integration in the integrations page.

## Getting started

1. Install the integration through HACS or manually as described above.
2. Configure the integration in Home Assistant. Go to Settings > Devices & Services > Local Solis/Ginglong Inverter. Enter the port you want to use for the server.
3. Configure the inverter's Wi-Fi datalogger to connect to your HA server IP address and the port you configured in the previous step.
4. Wait for the inverter to send data to the server (it might take a few minutes). You should see the data in Home Assistant. The integration will create a new device with all the sensors available in the inverter.

## Tested devices

_I was only able to test the integration with my own inverter. If you have a different model, please let me know if it works or not._

| Device              | Firmware version | Tested |
| ------------------- | ---------------- | ------ |
| S5-GR1P(0.7-3.6)K-M | v1.0             | ✅      |


## Acknowledgements

This would not be possible without the great work published by [@planetmarshall](https://github.com/planetmarshall/solis-service) for reverse engineering the protocol ([link to the blog post](https://www.algodynamic.co.uk/reverse-engineering-the-solisginlong-inverter-protocol.html)).
