# Thornwold March (level 18-28)
execute if score @s bc_zone matches 4 run return 0
scoreboard players set @s bc_zone 4
title @s times 8 55 15
title @s subtitle {"text":"Harsh ground · recommended level 18-28","color":"gray"}
title @s title {"text":"Thornwold March","color":"#4E9A5A"}
playsound minecraft:block.note_block.chime master @s ~ ~ ~ 0.7 1.2
tellraw @s ["",{"text":"\u00bb ","color":"dark_gray"},{"text":"Thornwold March","color":"#4E9A5A","bold":true},{"text":" \u00b7 harsh ground · recommended level 18-28","color":"gray"}]
