# radio_cli Release Notes

## Version 2.0.2
* Fixed bug which prevented FM tuning on a non-FMHD Si468x chip

## Version 2.0.1
* Now decoding FMHD radio, if available for a certain FM frequency

## Version 2.0.0
* Improved the -j flag. When used, it will now suppress the output of static text and always return a json or a json encapsulated error message.
* Firmware updated to DAB v6.0.6 and FMHD v5.1.3

## Version 1.4.0
* The station's text (e.g. name of the song) can now be output using the new -D command. Works only after the station has sent new data.

## Version 1.3.0
* The RDS status information command now shows the currently tuned FM frequency and other information
* Added a command to tune to the previous FM frequency

## Version 1.2.1
* Added support for the Raspberry Pi Zero W

## Version 1.2.0
* Added support for the Raspberry Pi 4B (BCM2711 processor)

## Version 1.1.0
* Added new functionality ```frequency_list``` to use a non-standard DAB frequency table (as for example for Korea)
* Added new functionality ```fm_frequency``` to tune to a given FM frequency in kHz 

## Version 1.0.0
* Initial release
