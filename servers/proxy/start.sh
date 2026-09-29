#!/usr/bin/env bash
cd "$(dirname "$0")"
exec java -Xms512M -Xmx512M -XX:+UseG1GC -XX:G1HeapRegionSize=4M \
  -XX:+UnlockExperimentalVMOptions -XX:+ParallelRefProcEnabled \
  -XX:+AlwaysPreTouch -XX:MaxInlineLevel=15 -jar velocity.jar
