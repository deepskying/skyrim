Scriptname AARedDrawFX extends ReferenceAlias
; Player-only prototype. A separate, unskinned FX node defaults to scale zero.
; Bow geometry and its seven animation bones are never modified by this script.
Actor owner
Weapon experimentBow
Bool drawing = False
Bool sawDrawn = False
Bool eventsBound = False
Float drawStarted = 0.0
String fxNode = "AAHexagramDrawFX"

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

Bool Function CanShow()
    Return owner && experimentBow && owner.GetEquippedWeapon() == experimentBow && owner.IsWeaponDrawn() && !owner.IsDead()
EndFunction

Function SetVisible(Bool showFX)
    Float size = 0.0
    If showFX
        size = 1.0
    EndIf
    ; Always write both views: switching camera or replacing the loaded 3D can
    ; create a fresh, hidden node even when the logical draw state did not change.
    NetImmerse.SetNodeScale(owner, fxNode, size, False)
    NetImmerse.SetNodeScale(owner, fxNode, size, True)
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
        RegisterForSingleUpdate(0.12)
    Else
        ClearDraw()
        RegisterForSingleUpdate(1.0)
    EndIf
EndEvent

Event OnObjectEquipped(Form akBaseObject, ObjectReference akReference)
    If akBaseObject == experimentBow
        ClearDraw()
        BindEvents()
        UnregisterForUpdate()
        RegisterForSingleUpdate(0.12)
    EndIf
EndEvent

Event OnObjectUnequipped(Form akBaseObject, ObjectReference akReference)
    If akBaseObject == experimentBow
        ClearDraw()
    EndIf
EndEvent

Event OnRaceSwitchComplete()
    Initialize()
EndEvent

Event OnCellLoad()
    BindEvents()
EndEvent
