Scriptname CMController extends Quest

; Actor aliases 0..63, matching home aliases 64..127.
ReferenceAlias Function MemberAlias(Int slot)
    If slot < 0 || slot >= 64
        Return None
    EndIf
    Return GetAlias(slot) as ReferenceAlias
EndFunction

; Release only the vanilla human recruitment slot after our own binding succeeds.
; Never call DismissFollower: it would stop the teammate and run dismissal side effects.
Bool Function DetachDialogueFollower(Actor who, Int slot)
    ReferenceAlias member = MemberAlias(slot)
    DialogueFollowerScript dialogue = Game.GetFormFromFile(0x000750BA, "Skyrim.esm") as DialogueFollowerScript
    If who == None || member == None || dialogue == None
        Return False
    EndIf
    If member.GetActorReference() != who || !who.IsPlayerTeammate() || who.IsDead()
        Return False
    EndIf
    If UI.IsMenuOpen("Dialogue Menu") || dialogue.iFollowerDismiss != 0
        Return False
    EndIf
    ReferenceAlias original = dialogue.pFollowerAlias
    ReferenceAlias expected = dialogue.GetAlias(0) as ReferenceAlias
    GlobalVariable expectedCount = Game.GetFormFromFile(0x000BCC98, "Skyrim.esm") as GlobalVariable
    If original == None || dialogue.pPlayerFollowerCount == None
        Return False
    EndIf
    If original != expected || dialogue.pPlayerFollowerCount != expectedCount
        Return False
    EndIf
    If original.GetActorReference() != who || dialogue.pPlayerFollowerCount.GetValue() != 1
        Return False
    EndIf
    original.UnregisterForUpdateGameTime()
    original.Clear()
    If original.GetReference() != None
        Return False
    EndIf
    dialogue.pPlayerFollowerCount.SetValue(0)
    dialogue.SetObjectiveDisplayed(10, False)
    who.SetPlayerTeammate(True, True)
    who.EvaluatePackage()
    Return member.GetActorReference() == who && who.IsPlayerTeammate()
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
