@echo off

for /l %%x in (0, 1, 249) do (
   aruco_print_marker.exe %%x ./36h12/%%x.png -d ARUCO_MIP_36h12 -bs 90 -e
)

pause