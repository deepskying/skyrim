Scriptname WEController extends Quest

FormList Property Markers Auto
FormList Property Bandits Auto
FormList Property Wolves Auto
FormList Property Trolls Auto
FormList Property Beasts Auto
FormList Property Extras Auto
Message Property Menu Auto
Message Property Robbery Auto
Message Property Directions Auto
Message Property Warning Auto
Message Property Help Auto
Faction Property SideA Auto
Faction Property SideB Auto
Spell Property SettingsPower Auto

Actor[] members
Int count = 0
Int eventType = -1
Int split = 0
Float age = 0.0
Float cooldown = 45.0
Float interval = 5.0
Float frequency = 0.5
Bool frequentDefaultApplied = False
Float lastX = 0.0
Float lastY = 0.0
Bool enabled = True
Bool busy = False
Bool speaking = False
Bool resolved = False
ObjectReference anchor

Event OnInit()
    members = new Actor[20]
    frequentDefaultApplied = True
    WEPools.Populate(Extras)
    Game.GetPlayer().AddSpell(SettingsPower, False)
    RegisterForSingleUpdate(interval)
EndEvent

Function Resume()
    ; The player alias repairs a pending timer after loading an existing save.
    ; Never discard members here: their references belong to the saved event.
    WEPools.Populate(Extras)
    Game.GetPlayer().AddSpell(SettingsPower, False)
    ; Apply the requested frequent preset once to pre-0.2.1 saves, then
    ; preserve subsequent choices made in the settings menu.
    If !frequentDefaultApplied
        If frequency > 0.0
            cooldown = cooldown * 0.5 / frequency
        EndIf
        frequency = 0.5
        frequentDefaultApplied = True
    EndIf
    If cooldown < 30.0
        cooldown = 30.0
    EndIf
    UnregisterForUpdate()
    RegisterForSingleUpdate(interval)
EndFunction

Bool Function Outdoors()
    Actor player = Game.GetPlayer()
    If player.IsDead() || player.IsInCombat() || player.IsFlying() || player.IsOnMount()
        Return False
    EndIf
    If player.GetParentCell() == None || player.GetParentCell().IsInterior()
        Return False
    EndIf
    ; Vanilla road markers are available in Tamriel. Other worldspaces are skipped.
    If player.GetWorldSpace() != Game.GetFormFromFile(0x0000003C, "Skyrim.esm") as WorldSpace
        Return False
    EndIf
    Return !Forbidden(player.GetCurrentLocation())
EndFunction

Bool Function Forbidden(Location place)
    While place != None
        If place.HasKeyword(Game.GetFormFromFile(0x00013168, "Skyrim.esm") as Keyword) || place.HasKeyword(Game.GetFormFromFile(0x00013166, "Skyrim.esm") as Keyword) || place.HasKeyword(Game.GetFormFromFile(0x000FC1A3, "Skyrim.esm") as Keyword)
            Return True
        EndIf
        place = place.GetParent()
    EndWhile
    Return False
EndFunction

ObjectReference Function FindAnchor()
    Actor player = Game.GetPlayer()
    Int size = Markers.GetSize()
    Int start = Utility.RandomInt(0, size - 1)
    Int n = 0
    While n < size
        ObjectReference point = Markers.GetAt((start + n) % size) as ObjectReference
        If point != None && !point.IsDisabled() && point.GetWorldSpace() == player.GetWorldSpace()
            Float distance = point.GetDistance(player)
            Float heading = player.GetHeadingAngle(point)
            ; Behind the player's facing direction, at a Bethesda encounter marker.
            If distance >= 1800.0 && distance <= 4200.0 && Math.Abs(heading) > 100.0
                If point.GetParentCell() != None && point.GetParentCell().IsAttached() && !Forbidden(point.GetCurrentLocation())
                    ; Leave existing vanilla encounters and residents alone.
                    If Game.FindClosestActorFromRef(point, 500.0) == None
                        Return point
                    EndIf
                EndIf
            EndIf
        EndIf
        n += 1
    EndWhile
    Return None
EndFunction

FormList Function PickPool()
    Int roll = Utility.RandomInt(0, 99)
    If roll < 25
        Return Bandits
    ElseIf roll < 45
        Return Wolves
    ElseIf roll < 55 && Game.GetPlayer().GetLevel() >= 10
        Return Trolls
    ElseIf roll >= 65 && Extras.GetSize() > 0
        FormList selected = WEPools.Choose(Extras, Game.GetPlayer().GetLevel())
        If selected != None
            Return selected
        EndIf
    EndIf
    Return Beasts
EndFunction

Actor Function Spawn(FormList pool, Int slot, Int team, Bool peaceful = False)
    Form base = pool.GetAt(Utility.RandomInt(0, pool.GetSize() - 1))
    If base == None
        Return None
    EndIf
    ObjectReference created = anchor.PlaceAtMe(base, 1, True, True)
    Actor who = created as Actor
    If who == None
        If created != None
            created.Delete()
        EndIf
        Return None
    EndIf
    ActorBase actualBase = who.GetActorBase()
    If actualBase == None || actualBase.IsEssential() || actualBase.IsProtected() || actualBase.IsUnique()
        who.Delete()
        Return None
    EndIf
    ; Track ownership before any latent operation, including MoveTo/Enable.
    members[slot] = who
    count = slot + 1
    who.MoveTo(anchor, Utility.RandomFloat(-80.0, 80.0), Utility.RandomFloat(-80.0, 80.0), 0.0)
    who.RemoveFromAllFactions()
    who.SetCrimeFaction(None)
    who.SetActorValue("Aggression", 0.0)
    who.SetActorValue("Confidence", 4.0)
    If team == 0
        who.AddToFaction(SideA)
    Else
        who.AddToFaction(SideB)
    EndIf
    If peaceful
        who.SetRestrained(True)
    EndIf
    who.Enable(False)
    Return who
EndFunction

Function AttackPlayer()
    Int i = 0
    While i < count
        If members[i] != None && !members[i].IsDead()
            members[i].SetRestrained(False)
            members[i].SetActorValue("Aggression", 2.0)
            members[i].StartCombat(Game.GetPlayer())
        EndIf
        i += 1
    EndWhile
    resolved = True
EndFunction

Function StandDown()
    Int i = 0
    While i < count
        If members[i] != None && !members[i].IsDead()
            members[i].SetActorValue("Aggression", 0.0)
            members[i].StopCombatAlarm()
            members[i].SetRestrained(False)
        EndIf
        i += 1
    EndWhile
    resolved = True
EndFunction

Function Begin(Int forcedType = -1)
    If busy || speaking || count > 0 || !Outdoors()
        Return
    EndIf
    busy = True
    anchor = FindAnchor()
    If anchor == None
        cooldown = 20.0
        busy = False
        Return
    EndIf
    Int roll = Utility.RandomInt(0, 99)
    eventType = 0
    If roll >= 60 && roll < 85
        eventType = Utility.RandomInt(1, 4)
    ElseIf roll >= 85
        eventType = 5
    EndIf
    If forcedType >= 0 && forcedType <= 5
        eventType = forcedType
    EndIf
    Int total = Utility.RandomInt(3, 20)
    FormList pool = PickPool()
    If eventType >= 1 && eventType <= 4
        pool = Bandits
    EndIf
    split = total / 2
    Int i = 0
    Bool failed = False
    While i < total && !failed
        Int team = 0
        If eventType == 5 && i >= split
            team = 1
            pool = Wolves
        EndIf
        If Spawn(pool, i, team, eventType >= 1 && eventType <= 4) == None
            failed = True
        EndIf
        i += 1
    EndWhile
    age = 0.0
    resolved = False
    cooldown = Utility.RandomFloat(180.0, 420.0) * frequency
    lastX = Game.GetPlayer().GetPositionX()
    lastY = Game.GetPlayer().GetPositionY()
    If failed
        ; Roll back the entire event; never leave an accidental undersized group.
        Cleanup(True)
    ElseIf eventType == 0
        AttackPlayer()
    ElseIf eventType == 5
        i = 0
        While i < count
            If i < split
                members[i].StartCombat(members[split])
            Else
                members[i].StartCombat(members[0])
            EndIf
            i += 1
        EndWhile
        resolved = True
    Else
        Debug.Notification("路边有人正在向你招呼。")
    EndIf
    busy = False
EndFunction

Function Story()
    Actor player = Game.GetPlayer()
    If speaking || busy || resolved || count == 0 || player.IsDead() || player.IsInCombat()
        Return
    EndIf
    Actor leader = members[0]
    If leader == None || leader.IsDead()
        StandDown()
        Return
    EndIf
    If leader.GetDistance(player) > 650.0
        Return
    EndIf
    speaking = True
    Int answer = -1
    If eventType == 1
        Int toll = player.GetLevel() * 15 + 50
        answer = Robbery.Show(toll)
        If answer == 0
            Form gold = Game.GetFormFromFile(0x0000000F, "Skyrim.esm")
            If player.GetItemCount(gold) >= toll
                player.RemoveItem(gold, toll, True)
                StandDown()
            Else
                Debug.MessageBox("强盗头目：钱不够？那就把装备留下！")
                AttackPlayer()
            EndIf
        ElseIf answer == 1 && player.GetActorValue("Speechcraft") >= Utility.RandomInt(25, 80)
            Debug.MessageBox("强盗头目：算你走运。弟兄们，让他过去。")
            StandDown()
        Else
            AttackPlayer()
        EndIf
    ElseIf eventType == 2
        answer = Directions.Show()
        If answer == 0 && Utility.RandomInt(0, 99) < 35
            Debug.MessageBox("问路人：谢谢你停下来。现在，交出你的钱！")
            AttackPlayer()
        Else
            StandDown()
        EndIf
    ElseIf eventType == 3
        answer = Warning.Show()
        ; Warning party leaves peacefully. Heeding the warning grants a longer break.
        If answer == 0
            cooldown += 120.0
        EndIf
        StandDown()
    ElseIf eventType == 4
        answer = Help.Show()
        If answer == 0
            Debug.MessageBox("领路人：谢谢！附近有强盗，我们一起守住这里！")
            ; A second group is not spawned: turn half of the existing 3-20
            ; participants into the ambushers, keeping the event budget bounded.
            Int i = 0
            While i < count
                members[i].SetRestrained(False)
                If i >= split
                    members[i].RemoveFromFaction(SideA)
                    members[i].AddToFaction(SideB)
                    members[i].StartCombat(player)
                EndIf
                i += 1
            EndWhile
            i = 0
            While i < split
                members[i].StartCombat(members[split])
                i += 1
            EndWhile
            resolved = True
        Else
            StandDown()
        EndIf
    EndIf
    speaking = False
EndFunction

Function Cleanup(Bool rollback = False)
    If speaking
        Return
    EndIf
    Actor player = Game.GetPlayer()
    Int i = 0
    If !rollback
        While i < count
            Actor who = members[i]
            If who != None && who.GetWorldSpace() == player.GetWorldSpace() && !player.GetParentCell().IsInterior()
                If who.GetDistance(player) < 7000.0
                    Return
                EndIf
                If who.IsInCombat() && who.GetDistance(player) < 12000.0
                    Return
                EndIf
            EndIf
            i += 1
        EndWhile
        If age < 300.0
            Return
        EndIf
    EndIf
    i = 0
    While i < count
        Actor owned = members[i]
        If owned != None
            owned.SetRestrained(False)
            owned.StopCombatAlarm()
            owned.Disable(False)
            owned.Delete()
            members[i] = None
        EndIf
        i += 1
    EndWhile
    count = 0
    anchor = None
    eventType = -1
EndFunction

Event OnUpdate()
    If !Utility.IsInMenuMode() && !busy && !speaking
        If enabled && cooldown > 0.0
            cooldown -= interval
        EndIf
        If count > 0
            age += interval
            ; Abort a pending conversation if a traveller has already been attacked.
            If !resolved && members[0] != None && members[0].IsInCombat()
                AttackPlayer()
            EndIf
            Story()
            Cleanup()
        ElseIf enabled
            Float dx = Game.GetPlayer().GetPositionX() - lastX
            Float dy = Game.GetPlayer().GetPositionY() - lastY
            If cooldown <= 0.0 && dx * dx + dy * dy >= 1500000.0
                Begin()
            EndIf
        EndIf
    EndIf
    RegisterForSingleUpdate(interval)
EndEvent

Function Settings()
    If speaking || busy
        Return
    EndIf
    speaking = True
    Int result = Menu.Show()
    If result == 0
        enabled = !enabled
        If enabled
            Debug.MessageBox("已开启野外遭遇。")
        Else
            Debug.MessageBox("已暂停新事件，已有事件会继续正常清理。")
        EndIf
    ElseIf result == 1
        frequency = 0.5
    ElseIf result == 2
        frequency = 1.0
    ElseIf result == 3
        frequency = 2.0
    EndIf
    speaking = False
    If result == 4
        If count > 0
            Debug.MessageBox("当前仍有一场遭遇。离开现场，等待清理后再试。")
        ElseIf !Outdoors()
            Debug.MessageBox("请在泰姆瑞尔野外、非战斗状态下测试。")
        Else
            Begin()
            If count == 0
                Debug.MessageBox("附近没有合适的原版遭遇标记。请继续沿野外道路行走后再试。")
            Else
                Debug.MessageBox("测试事件已生成，共 " + count + " 名成员。位于身后约 " + anchor.GetDistance(Game.GetPlayer()) + " 游戏单位。")
            EndIf
        EndIf
    EndIf
EndFunction
