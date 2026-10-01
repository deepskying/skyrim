Scriptname WELoadAlias extends ReferenceAlias

Event OnPlayerLoadGame()
    (GetOwningQuest() as WEController).Resume()
EndEvent
