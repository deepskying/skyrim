#pragma once
#include <algorithm>
#include <cstdint>
#include <map>
namespace rules {
inline constexpr float meter=69.99125f;
struct Mark {int stacks=0; float until=0;std::uint32_t cell=0;};
struct Marks {
    std::map<std::pair<std::uint32_t,std::uint32_t>,Mark> marks;
    void expire(float now){std::erase_if(marks,[&](auto& p){return p.second.until<=now;});}
    bool hit(std::uint32_t caster,std::uint32_t target,float now,std::uint32_t cell=0){
        expire(now);auto key=std::pair{caster,target};
        if(!marks.contains(key)){
            int count=0;auto oldest=marks.end();
            for(auto it=marks.begin();it!=marks.end();++it)if(it->first.first==caster){++count;if(oldest==marks.end()||it->second.until<oldest->second.until)oldest=it;}
            if(count>=16)marks.erase(oldest);
        }
        auto& m=marks[key];if(m.cell!=cell)m.stacks=0;m.cell=cell;m.until=now+4;
        if(++m.stacks==3){marks.erase(key);return true;}return false;
    }
};
inline int cap(int kind){return kind==1?1:kind==3?2:64;}
inline bool canStart(int kind,int active,int reserved){return active+reserved<cap(kind);}
inline float advance(float remaining,float delta,bool paused){return paused?remaining:std::max(0.f,remaining-std::max(0.f,delta));}
inline float segmentParameter(float px,float py,float pz,float ax,float ay,float az,float bx,float by,float bz){
    float x=bx-ax,y=by-ay,z=bz-az,den=x*x+y*y+z*z;
    return den<1e-6f?0.f:std::clamp(((px-ax)*x+(py-ay)*y+(pz-az)*z)/den,0.f,1.f);
}
}
