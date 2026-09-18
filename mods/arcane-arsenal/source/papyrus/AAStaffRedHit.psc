Scriptname AAStaffRedHit extends ActiveMagicEffect
Event OnEffectStart(Actor target, Actor caster)
    ; Only the primary red payload owns this script. Explosion payloads cannot
    ; recurse, and absorbed/blocked effects do not manufacture stack hits.
    AAStaffRuntime.RedApplied(caster, target)
EndEvent
