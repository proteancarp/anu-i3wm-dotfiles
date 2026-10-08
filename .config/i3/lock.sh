#!/bin/bash

# Force English weekday/month names without exporting a global locale override.
# This build checks LC_ALL first, so remove any inherited override for LC_TIME.
unset LC_ALL
export LC_TIME=C

# exec + --nofork lets xss-lock supervise the locker until unlock. This build
# releases the inherited sleep inhibitor itself when the lock window is mapped.
exec "$HOME/Downloads/i3lock-color/build/i3lock" \
  --nofork \
  --image="$HOME/Pictures/wallpapers/mountain.png" \
  --blur=10 \
  --inside-color=11191cff \
  --ring-color=657f91ff \
  --insidever-color=11191cff \
  --ringver-color=6f9291ff \
  --insidewrong-color=11191cff \
  --ringwrong-color=9b6b6bff \
  --line-color=11191cff \
  --ring-width=5 \
  --radius=85 \
  --greeter-color=11191c00 \
  --verif-color=11191c00 \
  --wrong-color=11191c00 \
  --ind-pos="x+w/2:y+h/2" \
  --greeter-pos="x+w/2:y+h/2+45" \
  --force-clock \
  --time-str="%H:%M" \
  --date-str="%A, %d %B" \
  --time-color=c8d1d5ff \
  --time-size=48 \
  --time-font="DejaVu Sans" \
  --time-pos="x+w/2:y+h/2-150" \
  --date-pos="tx:ty+30" \
  --date-color=c8d1d5cc \
  --date-size=16 \
  --date-font="DejaVu Sans" \
  --keyhl-color=6f9291ff \
  --bshl-color=46565bff
