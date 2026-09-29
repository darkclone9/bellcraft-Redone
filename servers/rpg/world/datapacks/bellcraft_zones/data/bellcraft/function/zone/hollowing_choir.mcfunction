scoreboard players set @s bc_hit 1
# The Hollowing Choir (level 70-80)
execute if score @s bc_zone matches 11 run return 0
scoreboard players set @s bc_zone 11
title @s times 8 55 15
title @s subtitle {"text":"Recommended level 70-80","color":"gray"}
title @s title {"text":"The Hollowing Choir","color":"#19D9EF"}
playsound minecraft:entity.warden_heartbeat master @s ~ ~ ~ 0.7 1
tellraw @s ["",{"text":"\u00bb ","color":"dark_gray"},{"text":"The Hollowing Choir","color":"#19D9EF","bold":true},{"text":" \u00b7 recommended level 70-80","color":"gray"}]
