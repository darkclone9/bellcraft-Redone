# Hearthvale (level 1-10)
execute if score @s bc_zone matches 1 run return 0
scoreboard players set @s bc_zone 1
title @s times 8 55 15
title @s subtitle {"text":"Recommended level 1-10","color":"gray"}
title @s title {"text":"Hearthvale","color":"#7FE08A"}
playsound minecraft:block.note_block.chime master @s ~ ~ ~ 0.7 1.4
tellraw @s ["",{"text":"\u00bb ","color":"dark_gray"},{"text":"Hearthvale","color":"#7FE08A","bold":true},{"text":" \u00b7 recommended level 1-10","color":"gray"}]
