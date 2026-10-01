Scriptname WESettingsEffect extends ActiveMagicEffect

Event OnEffectStart(Actor akTarget, Actor akCaster)
    WEController controller = Game.GetFormFromFile(0x00000800, "WildernessEncounters.esp") as WEController
    If controller != None
        controller.Settings()
    EndIf
EndEvent
