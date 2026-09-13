Scriptname CMController extends Quest

; Small native-to-Papyrus adapter. Policy and co-save records belong to the DLL.
Bool Function BindSlot(Actor who, Int slot, Bool active)
    If who == None || slot < 0 || slot >= 32
        Return False
    EndIf
    ReferenceAlias member = GetAlias(slot) as ReferenceAlias
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
    ReferenceAlias member = GetAlias(slot) as ReferenceAlias
    ReferenceAlias home = GetAlias(32 + slot) as ReferenceAlias
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
    ReferenceAlias home = GetAlias(32 + slot) as ReferenceAlias
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
    Actor who = (GetAlias(slot) as ReferenceAlias).GetActorReference()
    If who == None
        Return False
    EndIf
    who.GetActorBase().SetEssential(enabled)
    Return who.GetActorBase().IsEssential() == enabled
EndFunction
