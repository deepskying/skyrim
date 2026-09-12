Scriptname AARedDrawFX extends ReferenceAlias
; 48 zodiac, 24 geometric and 4 heteromorphic bows; preserve the existing alias identity.
; Bow geometry and its seven animation bones are never modified by this script.
Actor owner
Weapon experimentBow
Weapon[] ariesBows
String[] particleNodes
Bool drawing = False
Bool sawDrawn = False
Bool eventsBound = False
Float drawStarted = 0.0

Event OnInit()
    Initialize()
EndEvent

Event OnPlayerLoadGame()
    Initialize()
EndEvent

Function Initialize()
    UnregisterForUpdate()
    owner = Game.GetPlayer()
    experimentBow = Game.GetFormFromFile(0x811, "ArcaneArsenal.esp") as Weapon
    ariesBows = new Weapon[76]
    ariesBows[0] = Game.GetFormFromFile(0x811, "ArcaneArsenal.esp") as Weapon
    ariesBows[1] = Game.GetFormFromFile(0x814, "ArcaneArsenal.esp") as Weapon
    ariesBows[2] = Game.GetFormFromFile(0x817, "ArcaneArsenal.esp") as Weapon
    ariesBows[3] = Game.GetFormFromFile(0x81B, "ArcaneArsenal.esp") as Weapon
    ariesBows[4] = Game.GetFormFromFile(0x821, "ArcaneArsenal.esp") as Weapon
    ariesBows[5] = Game.GetFormFromFile(0x824, "ArcaneArsenal.esp") as Weapon
    ariesBows[6] = Game.GetFormFromFile(0x827, "ArcaneArsenal.esp") as Weapon
    ariesBows[7] = Game.GetFormFromFile(0x831, "ArcaneArsenal.esp") as Weapon
    ariesBows[8] = Game.GetFormFromFile(0x834, "ArcaneArsenal.esp") as Weapon
    ariesBows[9] = Game.GetFormFromFile(0x837, "ArcaneArsenal.esp") as Weapon
    ariesBows[10] = Game.GetFormFromFile(0x83A, "ArcaneArsenal.esp") as Weapon
    ariesBows[11] = Game.GetFormFromFile(0x83E, "ArcaneArsenal.esp") as Weapon
    ariesBows[12] = Game.GetFormFromFile(0x841, "ArcaneArsenal.esp") as Weapon
    ariesBows[13] = Game.GetFormFromFile(0x844, "ArcaneArsenal.esp") as Weapon
    ariesBows[14] = Game.GetFormFromFile(0x847, "ArcaneArsenal.esp") as Weapon
    ariesBows[15] = Game.GetFormFromFile(0x84A, "ArcaneArsenal.esp") as Weapon
    ariesBows[16] = Game.GetFormFromFile(0x84D, "ArcaneArsenal.esp") as Weapon
    ariesBows[17] = Game.GetFormFromFile(0x850, "ArcaneArsenal.esp") as Weapon
    ariesBows[18] = Game.GetFormFromFile(0x853, "ArcaneArsenal.esp") as Weapon
    ariesBows[19] = Game.GetFormFromFile(0x856, "ArcaneArsenal.esp") as Weapon
    ariesBows[20] = Game.GetFormFromFile(0x859, "ArcaneArsenal.esp") as Weapon
    ariesBows[21] = Game.GetFormFromFile(0x85C, "ArcaneArsenal.esp") as Weapon
    ariesBows[22] = Game.GetFormFromFile(0x85F, "ArcaneArsenal.esp") as Weapon
    ariesBows[23] = Game.GetFormFromFile(0x862, "ArcaneArsenal.esp") as Weapon
    ariesBows[24] = Game.GetFormFromFile(0x865, "ArcaneArsenal.esp") as Weapon
    ariesBows[25] = Game.GetFormFromFile(0x868, "ArcaneArsenal.esp") as Weapon
    ariesBows[26] = Game.GetFormFromFile(0x86B, "ArcaneArsenal.esp") as Weapon
    ariesBows[27] = Game.GetFormFromFile(0x86E, "ArcaneArsenal.esp") as Weapon
    ariesBows[28] = Game.GetFormFromFile(0x871, "ArcaneArsenal.esp") as Weapon
    ariesBows[29] = Game.GetFormFromFile(0x874, "ArcaneArsenal.esp") as Weapon
    ariesBows[30] = Game.GetFormFromFile(0x877, "ArcaneArsenal.esp") as Weapon
    ariesBows[31] = Game.GetFormFromFile(0x87A, "ArcaneArsenal.esp") as Weapon
    ariesBows[32] = Game.GetFormFromFile(0x87E, "ArcaneArsenal.esp") as Weapon
    ariesBows[33] = Game.GetFormFromFile(0x881, "ArcaneArsenal.esp") as Weapon
    ariesBows[34] = Game.GetFormFromFile(0x884, "ArcaneArsenal.esp") as Weapon
    ariesBows[35] = Game.GetFormFromFile(0x887, "ArcaneArsenal.esp") as Weapon
    ariesBows[36] = Game.GetFormFromFile(0x88B, "ArcaneArsenal.esp") as Weapon
    ariesBows[37] = Game.GetFormFromFile(0x88E, "ArcaneArsenal.esp") as Weapon
    ariesBows[38] = Game.GetFormFromFile(0x891, "ArcaneArsenal.esp") as Weapon
    ariesBows[39] = Game.GetFormFromFile(0x894, "ArcaneArsenal.esp") as Weapon
    ariesBows[40] = Game.GetFormFromFile(0x898, "ArcaneArsenal.esp") as Weapon
    ariesBows[41] = Game.GetFormFromFile(0x89B, "ArcaneArsenal.esp") as Weapon
    ariesBows[42] = Game.GetFormFromFile(0x89E, "ArcaneArsenal.esp") as Weapon
    ariesBows[43] = Game.GetFormFromFile(0x8A1, "ArcaneArsenal.esp") as Weapon
    ariesBows[44] = Game.GetFormFromFile(0x8A5, "ArcaneArsenal.esp") as Weapon
    ariesBows[45] = Game.GetFormFromFile(0x8A8, "ArcaneArsenal.esp") as Weapon
    ariesBows[46] = Game.GetFormFromFile(0x8AB, "ArcaneArsenal.esp") as Weapon
    ariesBows[47] = Game.GetFormFromFile(0x8AE, "ArcaneArsenal.esp") as Weapon
    ariesBows[48] = Game.GetFormFromFile(0x8B2, "ArcaneArsenal.esp") as Weapon
    ariesBows[49] = Game.GetFormFromFile(0x8B5, "ArcaneArsenal.esp") as Weapon
    ariesBows[50] = Game.GetFormFromFile(0x8B8, "ArcaneArsenal.esp") as Weapon
    ariesBows[51] = Game.GetFormFromFile(0x8BB, "ArcaneArsenal.esp") as Weapon
    ariesBows[52] = Game.GetFormFromFile(0x8BF, "ArcaneArsenal.esp") as Weapon
    ariesBows[53] = Game.GetFormFromFile(0x8C2, "ArcaneArsenal.esp") as Weapon
    ariesBows[54] = Game.GetFormFromFile(0x8C5, "ArcaneArsenal.esp") as Weapon
    ariesBows[55] = Game.GetFormFromFile(0x8C8, "ArcaneArsenal.esp") as Weapon



    ariesBows[56] = Game.GetFormFromFile(0x8CC, "ArcaneArsenal.esp") as Weapon
    ariesBows[57] = Game.GetFormFromFile(0x8CF, "ArcaneArsenal.esp") as Weapon
    ariesBows[58] = Game.GetFormFromFile(0x8D2, "ArcaneArsenal.esp") as Weapon
    ariesBows[59] = Game.GetFormFromFile(0x8D5, "ArcaneArsenal.esp") as Weapon

    ariesBows[60] = Game.GetFormFromFile(0x8D9, "ArcaneArsenal.esp") as Weapon
    ariesBows[61] = Game.GetFormFromFile(0x8DC, "ArcaneArsenal.esp") as Weapon
    ariesBows[62] = Game.GetFormFromFile(0x8DF, "ArcaneArsenal.esp") as Weapon
    ariesBows[63] = Game.GetFormFromFile(0x8E2, "ArcaneArsenal.esp") as Weapon

    ariesBows[64] = Game.GetFormFromFile(0x8E6, "ArcaneArsenal.esp") as Weapon
    ariesBows[65] = Game.GetFormFromFile(0x8E9, "ArcaneArsenal.esp") as Weapon
    ariesBows[66] = Game.GetFormFromFile(0x8EC, "ArcaneArsenal.esp") as Weapon
    ariesBows[67] = Game.GetFormFromFile(0x8EF, "ArcaneArsenal.esp") as Weapon

    ariesBows[68] = Game.GetFormFromFile(0x8F3, "ArcaneArsenal.esp") as Weapon
    ariesBows[69] = Game.GetFormFromFile(0x8F6, "ArcaneArsenal.esp") as Weapon
    ariesBows[70] = Game.GetFormFromFile(0x8F9, "ArcaneArsenal.esp") as Weapon
    ariesBows[71] = Game.GetFormFromFile(0x8FC, "ArcaneArsenal.esp") as Weapon

    ariesBows[72] = Game.GetFormFromFile(0x900, "ArcaneArsenal.esp") as Weapon
    ariesBows[73] = Game.GetFormFromFile(0x903, "ArcaneArsenal.esp") as Weapon
    ariesBows[74] = Game.GetFormFromFile(0x906, "ArcaneArsenal.esp") as Weapon
    ariesBows[75] = Game.GetFormFromFile(0x909, "ArcaneArsenal.esp") as Weapon


    particleNodes = new String[6]
    particleNodes[0] = "AAAriesDust0"
    particleNodes[1] = "AAAriesDust1"
    particleNodes[2] = "AAAriesDust2"
    particleNodes[3] = "AAAriesDust3"
    particleNodes[4] = "AAAriesDust4"
    particleNodes[5] = "AAAriesDust5"
    drawing = False
    sawDrawn = False
    eventsBound = False
    If owner && experimentBow
        BindEvents()
        SetVisible(False)
        RegisterForSingleUpdate(0.5)
    EndIf
EndFunction

Function BindEvents()
    If !owner
        Return
    EndIf
    eventsBound = RegisterForAnimationEvent(owner, "bowDrawStart")
    RegisterForAnimationEvent(owner, "bowDrawn")
    RegisterForAnimationEvent(owner, "arrowRelease")
    RegisterForAnimationEvent(owner, "bowRelease")
    RegisterForAnimationEvent(owner, "bowReset")
    RegisterForAnimationEvent(owner, "attackStop")
    RegisterForAnimationEvent(owner, "weaponSheathe")
EndFunction

Bool Function IsManaged(Form item)
    If !item
        Return False
    EndIf
    If item == experimentBow
        Return True
    EndIf
    If ariesBows
        Return ariesBows.Find(item as Weapon) >= 0
    EndIf
    Return False
EndFunction

Bool Function CanShow()
    Return owner && IsManaged(owner.GetEquippedWeapon()) && owner.IsWeaponDrawn() && !owner.IsDead()
EndFunction

Function SyncView(Float particleSize, Bool firstPerson)
    ; Remove the previous draw hexagram; retain the legacy red particle effect.
    If NetImmerse.HasNode(owner, "AAHexagramDrawFX", firstPerson)
        NetImmerse.SetNodeScale(owner, "AAHexagramDrawFX", 0.0, firstPerson)
    EndIf
    If NetImmerse.HasNode(owner, "AARedDrawParticles", firstPerson)
        NetImmerse.SetNodeScale(owner, "AARedDrawParticles", particleSize, firstPerson)
    EndIf
    If particleNodes && NetImmerse.HasNode(owner, "AAAriesDust0", firstPerson)
        ; Recover after camera switches or 3D reloads. Only write changed scales.
        Int i = 0
        While i < 6
            If Math.abs(NetImmerse.GetNodeScale(owner, particleNodes[i], firstPerson) - particleSize) > 0.00001
                NetImmerse.SetNodeScale(owner, particleNodes[i], particleSize, firstPerson)
            EndIf
            i += 1
        EndWhile
    EndIf
EndFunction

Function SetVisible(Bool showFX)
    If !owner
        Return
    EndIf
    ; Native emitter matrices must remain invertible even while hidden.
    Float particleSize = 0.0001
    If showFX
        particleSize = 1.0
    EndIf
    SyncView(particleSize, False)
    SyncView(particleSize, True)
EndFunction

Function ClearDraw()
    drawing = False
    sawDrawn = False
    SetVisible(False)
EndFunction

Event OnAnimationEvent(ObjectReference akSource, String eventName)
    If akSource != owner
        Return
    EndIf
    If eventName == "bowDrawStart" || eventName == "bowDrawn"
        If CanShow()
            drawing = True
            drawStarted = Utility.GetCurrentRealTime()
            sawDrawn = eventName == "bowDrawn"
            SetVisible(True)
        EndIf
    Else
        ClearDraw()
    EndIf
EndEvent

Event OnUpdate()
    If !owner || !experimentBow
        Return
    EndIf
    If !eventsBound
        ; Start-game quests can initialize before the player's 3D is loaded.
        BindEvents()
    EndIf
    If CanShow()
        Bool graphDrawn = owner.GetAnimationVariableBool("bBowDrawn")
        If graphDrawn
            drawing = True
            sawDrawn = True
        ElseIf drawing && (sawDrawn || Utility.GetCurrentRealTime() - drawStarted > 3.0)
            ; Recovery if a replacement animation fails to send its reset event.
            drawing = False
            sawDrawn = False
        EndIf
        SetVisible(drawing)
        RegisterForSingleUpdate(0.25)
    Else
        ClearDraw()
        RegisterForSingleUpdate(1.0)
    EndIf
EndEvent

Event OnObjectEquipped(Form akBaseObject, ObjectReference akReference)
    If IsManaged(akBaseObject)
        ClearDraw()
        BindEvents()
        UnregisterForUpdate()
        RegisterForSingleUpdate(0.25)
    EndIf
EndEvent

Event OnObjectUnequipped(Form akBaseObject, ObjectReference akReference)
    If IsManaged(akBaseObject)
        ClearDraw()
    EndIf
EndEvent

Event OnRaceSwitchComplete()
    Initialize()
EndEvent

Event OnCellLoad()
    BindEvents()
EndEvent
