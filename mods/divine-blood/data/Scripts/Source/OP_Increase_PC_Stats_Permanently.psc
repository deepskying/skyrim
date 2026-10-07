Scriptname OP_Increase_PC_Stats_Permanently extends ActiveMagicEffect

String Property increase_attr = "health" Auto
Message Property mIncrease_Health_Notify Auto
Message Property mIncrease_Magicka_Notify Auto
Message Property mIncrease_Stamina_Notify Auto
Message Property mIncrease_CarryWeight_Notify Auto

Event OnEffectStart(Actor akTarget, Actor akCaster)
    Actor player = Game.GetPlayer()
    If akTarget != player
        Return
    EndIf
    If increase_attr == "health"
        player.ModActorValue("Health", 1)
        Debug.Notification("&#29983;&#21629;&#19978;&#38480; +1")
    ElseIf increase_attr == "magicka"
        player.ModActorValue("Magicka", 1)
        Debug.Notification("&#39764;&#21147;&#19978;&#38480; +1")
    ElseIf increase_attr == "stamina"
        player.ModActorValue("Stamina", 1)
        Debug.Notification("&#20307;&#21147;&#19978;&#38480; +1")
    ElseIf increase_attr == "carry_weight"
        player.ModActorValue("CarryWeight", 1)
        Debug.Notification("&#36127;&#37325;&#19978;&#38480; +1")
    ElseIf increase_attr == "health_rec"
        player.ModActorValue("HealRate", 0.01)
        Debug.Notification("&#29983;&#21629;&#24674;&#22797; +0.01")
    ElseIf increase_attr == "magicka_rec"
        player.ModActorValue("MagickaRate", 0.01)
        Debug.Notification("&#39764;&#21147;&#24674;&#22797; +0.01")
    ElseIf increase_attr == "stamina_rec"
        player.ModActorValue("StaminaRate", 0.01)
        Debug.Notification("&#20307;&#21147;&#24674;&#22797; +0.01")
    ElseIf increase_attr == "shout_rec"
        Float cooldown = player.GetActorValue("ShoutRecoveryMult")
        Float delta = 0.0001
        If cooldown <= 0
            Return
        ElseIf cooldown < delta
            delta = cooldown
        EndIf
        player.ModActorValue("ShoutRecoveryMult", -delta)
        Debug.Notification("&#40857;&#21564;&#20919;&#21364;&#20493;&#29575; &#8722;0.0001")
    ElseIf increase_attr == "magic_resist"
        player.ModActorValue("MagicResist", 0.01)
        Debug.Notification("&#39764;&#27861;&#25239;&#24615; +0.01")
    ElseIf increase_attr == "fire_resist"
        player.ModActorValue("FireResist", 0.01)
        Debug.Notification("&#28779;&#28976;&#25239;&#24615; +0.01")
    ElseIf increase_attr == "frost_resist"
        player.ModActorValue("FrostResist", 0.01)
        Debug.Notification("&#23506;&#38684;&#25239;&#24615; +0.01")
    ElseIf increase_attr == "electric_resist"
        player.ModActorValue("ElectricResist", 0.01)
        Debug.Notification("&#38378;&#30005;&#25239;&#24615; +0.01")
    ElseIf increase_attr == "disease_resist"
        player.ModActorValue("DiseaseResist", 0.01)
        Debug.Notification("&#30142;&#30149;&#25239;&#24615; +0.01")
    ElseIf increase_attr == "poison_resist"
        player.ModActorValue("PoisonResist", 0.01)
        Debug.Notification("&#27602;&#32032;&#25239;&#24615; +0.01")
    ElseIf increase_attr == "damage_resist"
        player.ModActorValue("DamageResist", 0.01)
        Debug.Notification("&#25252;&#30002;&#20540; +0.01")
    ElseIf increase_attr == "speed_mult"
        player.ModActorValue("SpeedMult", 0.01)
        Debug.Notification("&#31227;&#21160;&#36895;&#24230; +0.01")
    Else
        Return
    EndIf
    player.SendModEvent("DivineBloodAbsorbed", increase_attr, 1.0)
EndEvent
