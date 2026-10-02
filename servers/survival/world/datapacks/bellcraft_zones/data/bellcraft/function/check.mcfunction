scoreboard players set @s bc_hit 0
execute if score @s bc_hit matches 0 if biome ~ ~ ~ #bellcraft:hollowing_choir run function bellcraft:zone/hollowing_choir
execute if score @s bc_hit matches 0 if dimension minecraft:the_nether run function bellcraft:zone/cinderreach
execute if score @s bc_hit matches 0 if dimension minecraft:the_end run function bellcraft:zone/pale_crown
execute if score @s bc_hit matches 0 if dimension minecraft:overworld positioned 0 ~ 0 if entity @s[distance=..1000] run function bellcraft:zone/hearthvale
execute if score @s bc_hit matches 0 if dimension minecraft:overworld positioned 0 ~ 0 if entity @s[distance=..2200] run function bellcraft:zone/thornwold_march
execute if score @s bc_hit matches 0 if dimension minecraft:overworld positioned 0 ~ 0 if entity @s[distance=..3600] run function bellcraft:zone/ashenmoor_expanse
execute if score @s bc_hit matches 0 if dimension minecraft:overworld positioned 0 ~ 0 if entity @s[distance=..5000] run function bellcraft:zone/stormhollow_frontier
execute if score @s bc_hit matches 0 if dimension minecraft:overworld run function bellcraft:zone/sundered_wilds
