"""Stable legacy identifiers and the new, configurable crafting defaults."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'The Blood of Divines.esp'
# key, deity, local ALCH ID, MGEF ID, stat label, matching beneficial actor values
ROWS = [
 ('health','玛拉',0x800,0x801,'生命上限 +1',[24]),
 ('magicka','朱莉安诺斯',0x802,0x80A,'魔力上限 +1',[25]),
 ('stamina','海尔辛',0x803,0x809,'体力上限 +1',[26]),
 ('carry_weight','泽尼萨尔',0xD74,0x80B,'负重上限 +1',[32]),
 ('health_rec','斯丹达尔',0xD75,0xD76,'生命恢复 +0.01',[27,155]),
 ('magicka_rec','玛格努斯',0xD77,0xD78,'魔力恢复 +0.01',[28,156]),
 ('stamina_rec','塔洛斯',0xD79,0xD7A,'体力恢复 +0.01',[29,157]),
 ('shout_rec','阿卡托什',0xD7B,0xD7C,'龙吼冷却倍率 −0.0001',[86,28,156]),
 ('magic_resist','阿祖拉',0xD7D,0xD7E,'魔法抗性 +0.01',[44]),
 ('fire_resist','梅瑞狄亚',0xD80,0xD7F,'火焰抗性 +0.01',[41]),
 ('frost_resist','诺克图娜',0xD82,0xD81,'寒霜抗性 +0.01',[43]),
 ('electric_resist','波耶希亚',0xD84,0xD83,'闪电抗性 +0.01',[42]),
 ('disease_resist','魄伊特',0xD86,0xD85,'疾病抗性 +0.01',[45]),
 ('poison_resist','纳米拉',0xD88,0xD87,'毒素抗性 +0.01',[40]),
 ('damage_resist','大衮',0xD8A,0xD89,'护甲值 +0.01',[39,9]),
 ('speed_mult','凯娜瑞斯',0xD8C,0xD8B,'移动速度 +0.01',[30,26]),
]

def catalog():
    return [dict(key=k,name=n+'之血',form=f,effect=e,gain=g,actorValues=a,
                 soulCost=10,alchemyCost=10,pointsPerIngredient=1)
            for k,n,f,e,g,a in ROWS]
