# Ashenmoor Expanse (level 20-32)
execute if score @s bc_zone matches 5 run return 0
scoreboard players set @s bc_zone 5
title @s times 8 55 15
title @s subtitle {"text":"Recommended level 20-32","color":"gray"}
title @s title {"text":"Ashenmoor Expanse","color":"#E0B15A"}
playsound minecraft:block.note_block.bell master @s ~ ~ ~ 0.7 1.1
tellraw @s ["",{"text":"\u00bb ","color":"dark_gray"},{"text":"Ashenmoor Expanse","color":"#E0B15A","bold":true},{"text":" \u00b7 recommended level 20-32","color":"gray"}]
