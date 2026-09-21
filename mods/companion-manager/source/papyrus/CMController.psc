Scriptname CMController extends Quest

Bool Function ResetActivityTargets()
    Int slot = 0
    While slot < 64
        ReferenceAlias goal = GetAlias(slot + 128) as ReferenceAlias
        If goal == None
            Return False
        EndIf
        If goal.GetReference() != None
            EndActivity(slot)
        EndIf
        slot += 1
    EndWhile
    Return True
EndFunction

Bool Function BeginActivity(Int slot, ObjectReference target)
    ReferenceAlias member = MemberAlias(slot)
    ReferenceAlias goal = GetAlias(slot + 128) as ReferenceAlias
    If member == None || goal == None || target == None
        Return False
    EndIf
    Actor who = member.GetActorReference()
    If who == None || who.IsInCombat() || Game.GetPlayer().IsInCombat()
        Return False
    EndIf
    goal.ForceRefTo(target)
    Return goal.GetReference() == target
EndFunction

Bool Function FaceActivity(Int slot, Bool looting, Bool trading)
    ReferenceAlias member = MemberAlias(slot)
    ReferenceAlias goal = GetAlias(slot + 128) as ReferenceAlias
    If member == None || goal == None
        Return False
    EndIf
    Actor who = member.GetActorReference()
    ObjectReference target = goal.GetReference()
    If who == None || target == None || who.IsInCombat() || Game.GetPlayer().IsInCombat()
        Return False
    EndIf
    who.SetAngle(who.GetAngleX(), who.GetAngleY(), who.GetAngleZ() + who.GetHeadingAngle(target))
    who.SetLookAt(target)
    If trading
        Actor merchant = target as Actor
        If merchant == None || merchant.IsInCombat()
            Return False
        EndIf
        merchant.SetLookAt(who)
    EndIf
    If looting
        If (target as Actor) != None
            who.PlayIdle(Game.GetFormFromFile(0x000EFC64, "Skyrim.esm") as Idle)
        Else
            who.PlayIdle(Game.GetFormFromFile(0x00075C3E, "Skyrim.esm") as Idle)
        EndIf
    EndIf
    Return True
EndFunction

Bool Function EndActivity(Int slot)
    ReferenceAlias member = MemberAlias(slot)
    ReferenceAlias goal = GetAlias(slot + 128) as ReferenceAlias
    If goal != None
        Actor other = goal.GetReference() as Actor
        If other != None && other != Game.GetPlayer() && !other.IsDead()
            other.ClearLookAt()
        EndIf
        goal.Clear()
    EndIf
    If member != None
        Actor who = member.GetActorReference()
        If who != None
            who.ClearLookAt()
            If !who.IsInCombat()
                Debug.SendAnimationEvent(who, "IdleForceDefaultState")
            EndIf
            who.EvaluatePackage()
        EndIf
    EndIf
    Return True
EndFunction

; Actor aliases 0..63, matching home aliases 64..127.
ReferenceAlias Function MemberAlias(Int slot)
    If slot < 0 || slot >= 64
        Return None
    EndIf
    Return GetAlias(slot) as ReferenceAlias
EndFunction

; Release only the vanilla human recruitment slot after our own binding succeeds.
; Never call DismissFollower: it would stop the teammate and run dismissal side effects.
Bool Function DetachDialogueFollower(Actor who, Int slot, Bool active)
    ReferenceAlias member = MemberAlias(slot)
    DialogueFollowerScript dialogue = Game.GetFormFromFile(0x000750BA, "Skyrim.esm") as DialogueFollowerScript
    If who == None || member == None || dialogue == None
        Return False
    EndIf
    If member.GetActorReference() != who || who.IsDead()
        Return False
    EndIf
    If UI.IsMenuOpen("Dialogue Menu") || dialogue.iFollowerDismiss != 0
        Return False
    EndIf
    ReferenceAlias original = dialogue.pFollowerAlias
    ReferenceAlias expected = dialogue.GetAlias(0) as ReferenceAlias
    GlobalVariable expectedCount = Game.GetFormFromFile(0x000BCC98, "Skyrim.esm") as GlobalVariable
    If original == None || expectedCount == None || dialogue.pPlayerFollowerCount == None
        Return False
    EndIf
    If original != expected || dialogue.pPlayerFollowerCount != expectedCount
        Debug.Trace("[CompanionManager] recruitment blocked: vanilla script properties differ")
        Return False
    EndIf
    Float count = expectedCount.GetValue()
    If count != 0 && count != 1
        Debug.Trace("[CompanionManager] recruitment blocked: unexpected count " + count)
        Return False
    EndIf
    ; GetReference also protects a non-actor alias occupant. Never clear someone else.
    ObjectReference occupant = original.GetReference()
    If occupant != None && occupant != who
        Return False
    EndIf
    ; Native code observes the same state across ticks. Recheck immediately before writing.
    If occupant == who
        original.UnregisterForUpdateGameTime()
        original.Clear()
    EndIf
    If original.GetReference() != None
        Return False
    EndIf
    expectedCount.SetValue(0)
    dialogue.SetObjectiveDisplayed(10, False)
    who.SetPlayerTeammate(active, active)
    who.EvaluatePackage()
    Return member.GetActorReference() == who && who.IsPlayerTeammate() == active && expectedCount.GetValue() == 0
EndFunction

ReferenceAlias Function HomeAlias(Int slot)
    If slot < 0 || slot >= 64
        Return None
    EndIf
    Return GetAlias(slot + 64) as ReferenceAlias
EndFunction

; Small native-to-Papyrus adapter. Policy and co-save records belong to the DLL.
Bool Function BindSlot(Actor who, Int slot, Bool active)
    If who == None || slot < 0 || slot >= 64
        Return False
    EndIf
    ReferenceAlias member = MemberAlias(slot)
    If member == None
        Return False
    EndIf
    If member.GetReference() != None && member.GetReference() != who
        Return False
    EndIf
    member.ForceRefTo(who)
    If member.GetReference() != who
        Return False
    EndIf
    If !active
        Quest dialogueQuest = Game.GetFormFromFile(0x000750BA, "Skyrim.esm") as Quest
        If dialogueQuest != None
            ReferenceAlias original = dialogueQuest.GetAlias(0) as ReferenceAlias
            If original != None && original.GetReference() == who
                If !DetachDialogueFollower(who, slot, False)
                    Return False
                EndIf
            EndIf
        EndIf
    EndIf
    who.SetPlayerTeammate(active, active)
    who.EvaluatePackage()
    Return True
EndFunction

Bool Function ReleaseSlot(Int slot)
    ReferenceAlias member = MemberAlias(slot)
    ReferenceAlias home = HomeAlias(slot)
    If member == None || home == None
        Return False
    EndIf
    Actor who = member.GetActorReference()
    If who != None
        who.SetPlayerTeammate(False, False)
        member.Clear()
        who.EvaluatePackage()
    EndIf
    ObjectReference marker = home.GetReference()
    home.Clear()
    If marker != None
        marker.DisableNoWait()
        marker.Delete()
    EndIf
    Return member.GetReference() == None
EndFunction

Bool Function SetHome(Int slot, Bool clearHome)
    ReferenceAlias home = HomeAlias(slot)
    If home == None
        Return False
    EndIf
    ObjectReference marker = home.GetReference()
    If clearHome
        home.Clear()
        If marker != None
            marker.DisableNoWait()
            marker.Delete()
        EndIf
        Return True
    EndIf
    If marker == None
        marker = Game.GetPlayer().PlaceAtMe(Game.GetForm(0x0000003B), 1, True, False)
        If marker == None
            Return False
        EndIf
        home.ForceRefTo(marker)
    EndIf
    marker.MoveTo(Game.GetPlayer())
    Return home.GetReference() == marker
EndFunction

Bool Function SetProtection(Int slot, Bool enabled)
    ReferenceAlias member = MemberAlias(slot)
    If member == None
        Return False
    EndIf
    Actor who = member.GetActorReference()
    If who == None
        Return False
    EndIf
    who.GetActorBase().SetEssential(enabled)
    Return who.GetActorBase().IsEssential() == enabled
EndFunction


Bool Function CleanupRetiredNeeds()
    UnregisterForSleep()
    Int slot = 0
    While slot < 64
        ReferenceAlias target = GetAlias(192 + slot) as ReferenceAlias
        If target != None
            target.Clear()
        EndIf
        slot += 1
    EndWhile
    Return True
EndFunction
