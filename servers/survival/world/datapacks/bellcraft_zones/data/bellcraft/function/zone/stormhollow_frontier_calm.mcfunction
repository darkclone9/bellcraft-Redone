# Stormhollow Frontier (level 32-45)
execute if score @s bc_zone matches 7 run return 0
scoreboard players set @s bc_zone 7
title @s times 8 55 15
title @s subtitle {"text":"Recommended level 32-45","color":"gray"}
title @s title {"text":"Stormhollow Frontier","color":"#9FD8F0"}
playsound minecraft:block.note_block.bell master @s ~ ~ ~ 0.7 0.9
tellraw @s ["",{"text":"\u00bb ","color":"dark_gray"},{"text":"Stormhollow Frontier","color":"#9FD8F0","bold":true},{"text":" \u00b7 recommended level 32-45","color":"gray"}]
