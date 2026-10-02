# Stormhollow Frontier (level 40-53)
execute if score @s bc_zone matches 8 run return 0
scoreboard players set @s bc_zone 8
title @s times 8 55 15
title @s subtitle {"text":"Harsh ground · recommended level 40-53","color":"gray"}
title @s title {"text":"Stormhollow Frontier","color":"#9FD8F0"}
playsound minecraft:block.note_block.bell master @s ~ ~ ~ 0.7 0.9
tellraw @s ["",{"text":"\u00bb ","color":"dark_gray"},{"text":"Stormhollow Frontier","color":"#9FD8F0","bold":true},{"text":" \u00b7 harsh ground · recommended level 40-53","color":"gray"}]
