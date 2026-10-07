"""Compile the preserved Papyrus script identity using Caprica's Skyrim backend."""
from pathlib import Path
import subprocess
from catalog import ROOT, ROWS
GAME=Path('C:/Users/linos/Desktop/games/+skyrim/SkyrimSE')
REPO=ROOT.parents[1]
def main():
    source=ROOT/'data/Scripts/Source';source.mkdir(parents=True,exist_ok=True)
    script='Scriptname OP_Increase_PC_Stats_Permanently extends ActiveMagicEffect\n\nString Property increase_attr = "health" Auto\n'
    for key in ('Health','Magicka','Stamina','CarryWeight'):script+=f'Message Property mIncrease_{key}_Notify Auto\n'
    script+='\nEvent OnEffectStart(Actor akTarget, Actor akCaster)\n    Actor player = Game.GetPlayer()\n    If akTarget != player\n        Return\n    EndIf\n'
    attributes=['Health','Magicka','Stamina','CarryWeight','HealRate','MagickaRate','StaminaRate','ShoutRecoveryMult','MagicResist','FireResist','FrostResist','ElectricResist','DiseaseResist','PoisonResist','DamageResist','SpeedMult']
    for i,(row,av) in enumerate(zip(ROWS,attributes)):
        key,_,_,_,gain,_=row
        script+=f'    {"If" if i==0 else "ElseIf"} increase_attr == "{key}"\n'
        if key=='shout_rec':
            script+='        Float cooldown = player.GetActorValue("ShoutRecoveryMult")\n        Float delta = 0.0001\n        If cooldown <= 0\n            Return\n        ElseIf cooldown < delta\n            delta = cooldown\n        EndIf\n        player.ModActorValue("ShoutRecoveryMult", -delta)\n'
        else:script+=f'        player.ModActorValue("{av}", {1 if i<4 else 0.01})\n'
        notification=''.join(f'&#{ord(c)};' if ord(c)>127 else c for c in gain)
        script+=f'        Debug.Notification("{notification}")\n'
    script+='    Else\n        Return\n    EndIf\n    player.SendModEvent("DivineBloodAbsorbed", increase_attr, 1.0)\nEndEvent\n'
    p=source/'OP_Increase_PC_Stats_Permanently.psc';p.write_text(script,encoding='utf-8')
    # Vanilla import signatures plus SKSE's public Form.SendModEvent signature.
    imports=ROOT/'build/papyrus-imports';imports.mkdir(parents=True,exist_ok=True)
    (imports/'Form.psc').write_text((GAME/'Data/source/scripts/Form.psc').read_text(encoding='utf-8')+'\nFunction SendModEvent(String eventName, String strArg = "", Float numArg = 0.0) Native\n',encoding='utf-8')
    subprocess.run([str(REPO/'reference/caprica/Caprica.exe'),'--game=skyrim','--ignorecwd',
        '--import',str(source)+';'+str(imports)+';'+str(GAME/'Data/source/scripts'),
        '--flags',str(GAME/'Data/source/scripts/TESV_Papyrus_Flags.flg'),
        '--output',str(ROOT/'data/Scripts'),str(p)],check=True)
if __name__=='__main__':main()
