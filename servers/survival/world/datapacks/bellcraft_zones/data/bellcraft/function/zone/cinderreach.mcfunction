scoreboard players set @s bc_hit 1
# Cinderreach (level 55-70)
execute if score @s bc_zone matches 12 run return 0
scoreboard players set @s bc_zone 12
title @s times 8 55 15
title @s subtitle {"text":"Recommended level 55-70","color":"gray"}
title @s title {"text":"Cinderreach","color":"#E2683C"}
playsound minecraft:entity.blaze.ambient master @s ~ ~ ~ 0.7 1
tellraw @s ["",{"text":"\u00bb ","color":"dark_gray"},{"text":"Cinderreach","color":"#E2683C","bold":true},{"text":" \u00b7 recommended level 55-70","color":"gray"}]
