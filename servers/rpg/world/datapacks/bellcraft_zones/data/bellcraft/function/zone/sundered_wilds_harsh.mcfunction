# The Sundered Wilds (level 53-68)
execute if score @s bc_zone matches 10 run return 0
scoreboard players set @s bc_zone 10
title @s times 8 55 15
title @s subtitle {"text":"Harsh ground · recommended level 53-68","color":"gray"}
title @s title {"text":"The Sundered Wilds","color":"#9B6FD8"}
playsound minecraft:entity.elder_guardian.curse master @s ~ ~ ~ 0.7 1
tellraw @s ["",{"text":"\u00bb ","color":"dark_gray"},{"text":"The Sundered Wilds","color":"#9B6FD8","bold":true},{"text":" \u00b7 harsh ground · recommended level 53-68","color":"gray"}]
