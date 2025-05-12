# Keyboard lighting control for Tuxedo Stellaris Gen. 6 (and maybe others) 

## Switches the keyboard lighting on with a certain brightness and switches it off again after an adjustable period of inactivity.

## Why this little script?
Because by default the keyboard lighting is only switched off when the screen saver appears. This time span was too long for me personally.
The minimum brightness was also too bright for me personally.
This script also accepts values less than 10 (20%)

## Other Hardware
Adaptation to other hardware that also follows the sysfs standard for keyboard illumination should be feasible without any problems.

## How to use?
Just start the script in background (Root privilleges needed) or start it as a systemd service.
It take ```--brightness``` (1-50) and ```--timeout``` in seconds as parameters.
