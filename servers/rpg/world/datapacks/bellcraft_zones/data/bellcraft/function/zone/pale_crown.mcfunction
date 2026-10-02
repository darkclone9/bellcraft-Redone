scoreboard players set @s bc_hit 1
# The Pale Crown (level 80-99)
execute if score @s bc_zone matches 13 run return 0
scoreboard players set @s bc_zone 13
title @s times 8 55 15
title @s subtitle {"text":"Recommended level 80-99","color":"gray"}
title @s title {"text":"The Pale Crown","color":"#C89BF0"}
playsound minecraft:entity.enderman.stare master @s ~ ~ ~ 0.7 1
tellraw @s ["",{"text":"\u00bb ","color":"dark_gray"},{"text":"The Pale Crown","color":"#C89BF0","bold":true},{"text":" \u00b7 recommended level 80-99","color":"gray"}]
