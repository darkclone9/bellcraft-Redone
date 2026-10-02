# Hearthvale (level 9-18)
execute if score @s bc_zone matches 2 run return 0
scoreboard players set @s bc_zone 2
title @s times 8 55 15
title @s subtitle {"text":"Harsh ground · recommended level 9-18","color":"gray"}
title @s title {"text":"Hearthvale","color":"#7FE08A"}
playsound minecraft:block.note_block.chime master @s ~ ~ ~ 0.7 1.4
tellraw @s ["",{"text":"\u00bb ","color":"dark_gray"},{"text":"Hearthvale","color":"#7FE08A","bold":true},{"text":" \u00b7 harsh ground · recommended level 9-18","color":"gray"}]
