Scriptname OP_Increase_PC_Stats_Permanently extends activemagiceffect  

string Property increase_attr = "health" Auto

Message Property mIncrease_Health_Notify Auto
Message Property mIncrease_Magicka_Notify Auto
Message Property mIncrease_Stamina_Notify Auto
Message Property mIncrease_CarryWeight_Notify Auto


Event OnEffectStart(Actor AKTarget, Actor AKCaster)    
    if increase_attr == "health"
        Game.GetPlayer().ModActorValue("health",10)
        Debug.Notification("&#29983;&#21629;&#19978;&#38480;&#27704;&#20037;&#43;&#49;&#48;")
        ; mIncrease_Health_Notify.Show()
    ElseIf increase_attr == "magicka"
        Game.GetPlayer().ModActorValue("Magicka",10)
        Debug.Notification("&#39764;&#21147;&#19978;&#38480;&#27704;&#20037;&#43;&#49;&#48;")
        ; mIncrease_Magicka_Notify.Show()
    ElseIf increase_attr == "stamina"
        Game.GetPlayer().ModActorValue("Stamina",10)
        Debug.Notification("&#20307;&#21147;&#19978;&#38480;&#27704;&#20037;&#43;&#49;&#48;")
    ElseIf increase_attr == "carry_weight"
        Game.GetPlayer().ModActorValue("CarryWeight",10)
        Debug.Notification("&#36127;&#37325;&#19978;&#38480;&#27704;&#20037;&#43;&#49;&#48;")
        ; mIncrease_CarryWeight_Notify.Show()
    ElseIf increase_attr == "health_rec"
        Game.GetPlayer().ModActorValue("HealRate",0.01)
        Debug.Notification("&#29983;&#21629;&#22238;&#22797;&#27704;&#20037;&#43;&#48;&#46;&#48;&#49;")
    ElseIf increase_attr == "stamina_rec"
        Game.GetPlayer().ModActorValue("StaminaRate",0.01)
        Debug.Notification("&#20307;&#21147;&#22238;&#22797;&#27704;&#20037;&#43;&#48;&#46;&#48;&#49;")
    ElseIf increase_attr == "magicka_rec"
        Game.GetPlayer().ModActorValue("MagickaRate",0.01)
        Debug.Notification("&#39764;&#21147;&#22238;&#22797;&#27704;&#20037;&#43;&#48;&#46;&#48;&#49;")
    ElseIf increase_attr == "shout_rec"
        Game.GetPlayer().ModActorValue("ShoutRecoveryMult",-0.0001)
        float old=Game.GetPlayer().GetActorValue("ShoutRecoveryMult")
        if old<0
            Game.GetPlayer().SetActorValue("ShoutRecoveryMult",0)
            Debug.Notification("&#40857;&#21564;&#24050;&#26080;&#20919;&#21364;")
        Else
            Debug.Notification("&#40857;&#21564;&#20919;&#21364;&#45;&#48;&#46;&#48;&#49;")    
        endif
    ElseIf increase_attr == "magic_resist"
        Game.GetPlayer().ModActorValue("magicresist",0.01)
        Debug.Notification("&#39764;&#27861;&#25239;&#24615;&#27704;&#20037;&#43;&#48;&#46;&#48;&#49;")
    ElseIf increase_attr == "fire_resist"
        Game.GetPlayer().ModActorValue("fireresist",0.01)
        Debug.Notification("&#28779;&#28976;&#25239;&#24615;&#27704;&#20037;&#43;&#48;&#46;&#48;&#49;")
    ElseIf increase_attr == "frost_resist"
        Game.GetPlayer().ModActorValue("frostresist",0.01)
        Debug.Notification("&#23506;&#38684;&#25239;&#24615;&#27704;&#20037;&#43;&#48;&#46;&#48;&#49;")
    ElseIf increase_attr == "electric_resist"
        Game.GetPlayer().ModActorValue("electricresist",0.01)
        Debug.Notification("&#38378;&#30005;&#25239;&#24615;&#27704;&#20037;&#43;&#48;&#46;&#48;&#49;")
    ElseIf increase_attr == "disease_resist"
        Game.GetPlayer().ModActorValue("diseaseresist",0.01)
        Debug.Notification("&#30142;&#30149;&#25239;&#24615;&#27704;&#20037;&#43;&#48;&#46;&#48;&#49;")
    ElseIf increase_attr == "poison_resist"
        Game.GetPlayer().ModActorValue("poisonresist",0.01)
        Debug.Notification("&#27602;&#32032;&#25239;&#24615;&#27704;&#20037;&#43;&#48;&#46;&#48;&#49;")
    ElseIf increase_attr == "damage_resist"
        Game.GetPlayer().ModActorValue("damageresist",0.01)
        Debug.Notification("&#25915;&#20987;&#25239;&#24615;&#27704;&#20037;&#43;&#48;&#46;&#48;&#49;")
    ElseIf increase_attr == "speed_mult"
        Game.GetPlayer().ModActorValue("speedmult",0.01)
        Debug.Notification("&#31227;&#21160;&#36895;&#24230;&#27704;&#20037;&#43;&#48;&#46;&#48;&#49;")
    endif

EndEvent