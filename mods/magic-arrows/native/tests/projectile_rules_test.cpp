#include "projectile_rules.h"
#include <array>
#include <stdexcept>
#include <iostream>
using projectile_rules::Candidate;using projectile_rules::Choose;
void check(bool b){if(!b)throw std::runtime_error("concentration projectile selection failed");}
int main(){
    // Effective Mysticism Frostbite: frost jet, projectile-less slow, conditional perk missile.
    check(Choose(std::array{Candidate{8,true,true},Candidate{0,true,true},Candidate{1,true,true}})==0);
    // Cost-selected auxiliary effect / source order must not hide a valid jet.
    check(Choose(std::array{Candidate{1,true,true},Candidate{0,true,true},Candidate{8,true,true}})==2);
    check(Choose(std::array{Candidate{4,true,true},Candidate{16,true,false}})==1);
    check(Choose(std::array{Candidate{1,true,false},Candidate{0,true,false}})==-1);
    check(Choose(std::array{Candidate{8,false,false}})==-1);
    check(Choose(std::array{Candidate{8,true,false},Candidate{1,true,true}})==0); // Flames
    check(Choose({})==-1);
    std::cout<<"Concentration selection: Mysticism Frostbite, auxiliary ordering, unconditional preference, invalid delivery/type and empty spell passed.\n";
}
