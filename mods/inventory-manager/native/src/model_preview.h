#pragma once

#include "MeridianUIAPI/NifViewDllLoader.h"
#include "MeridianUIAPI/RenderLayerDllLoader.h"
#include <nlohmann/json.hpp>
#include <cmath>

// All methods run on Skyrim's task thread, including page requests.
class ModelPreview
{
public:
    void Initialize(Meridian::UI::Settings& settings)
    {
        layers_ = Meridian::UI::RenderLayer::Query(&settings, "InventoryManager");
        models_ = Meridian::UI::NifView::Query(&settings, "InventoryManager");
    }

    bool Available() const { return layers_ && models_; }

    void Clear()
    {
        if (surface_ && Available()) {
            layers_->SetVisible(surface_, false);
            models_->ClearModel(surface_);
        }
        selected_ = 0;
        layoutReady_ = false;
    }

    void Select(RE::FormID id)
    {
        Clear();
        if (!Available()) return;
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* item = RE::TESForm::LookupByID<RE::TESBoundObject>(id);
        if (!player || !item) return;
        const auto inventory = player->GetInventory();
        const auto entry = inventory.find(item);
        if (entry == inventory.end() || entry->second.first <= 0) return;
        const char* path = nullptr;
        if (auto* weapon = item->As<RE::TESObjectWEAP>()) path = weapon->GetModel();
        else if (auto* armor = item->As<RE::TESObjectARMO>()) {
            const auto* base = player->GetActorBase();
            const auto sex = base && base->GetSex() == RE::SEX::kFemale ? 1 : 0;
            path = armor->worldModels[sex].GetModel();
            if (!path || !*path) path = armor->worldModels[1 - sex].GetModel();
        }
        if (!path || !*path) return;
        if (!surface_) {
            Meridian::UI::RenderLayer::SurfaceCreateInfo info{};
            info.ownerName = "inventorymanager";
            info.surfaceName = "item-preview";
            // Only covers the dedicated empty HTML viewport; controls stay outside.
            info.zOrder = 100;
            surface_ = layers_->CreateSurface(&info);
        }
        if (!surface_) return;
        camera_ = {};
        Meridian::UI::NifView::NifLoadInfo load{};
        load.surface = surface_;
        load.modelPath = path;
        if (models_->LoadModel(&load)) {
            selected_ = id;
            models_->SetCamera(surface_, &camera_);
            logger::info("Preview requested: {:08X} {}", id, path);
        }
    }

    void Layout(const nlohmann::json& request)
    {
        if (!surface_ || !Available()) return;
        const auto x = request.value("x", -1);
        const auto y = request.value("y", -1);
        const auto w = request.value("width", 0);
        const auto h = request.value("height", 0);
        layoutReady_ = x >= 0 && y >= 0 && w > 0 && h > 0 &&
            x <= 16384 && y <= 16384 && w <= 8192 && h <= 8192 &&
            layers_->SetRect(surface_, x, y, w, h);
        if (!layoutReady_) layers_->SetVisible(surface_, false);
    }

    void Camera(const nlohmann::json& request)
    {
        if (!surface_ || !Available()) return;
        const auto yaw = request.value("yaw", 35.0f);
        const auto pitch = request.value("pitch", 15.0f);
        const auto distance = request.value("distance", 1.0f);
        if (!std::isfinite(yaw) || !std::isfinite(pitch) || !std::isfinite(distance)) return;
        camera_.yawDegrees = std::fmod(yaw, 360.0f);
        camera_.pitchDegrees = std::clamp(pitch, -85.0f, 85.0f);
        camera_.distanceScale = std::clamp(distance, 0.25f, 4.0f);
        models_->SetCamera(surface_, &camera_);
    }

    const char* Status(RE::FormID id, bool focused)
    {
        if (!Available()) return "unavailable";
        if (!surface_ || id != selected_ || !id) return "unsupported";
        const auto status = models_->GetStatus(surface_);
        using Status = Meridian::UI::NifView::Status;
        layers_->SetVisible(surface_, focused && layoutReady_ && status == Status::Ready);
        switch (status) {
        case Status::Loading: return "loading";
        case Status::Ready: return "ready";
        case Status::Failed: return "failed";
        default: return "unsupported";
        }
    }

private:
    Meridian::UI::RenderLayer::IRenderLayerAPI* layers_ = nullptr;
    Meridian::UI::NifView::INifViewAPI* models_ = nullptr;
    Meridian::UI::RenderLayer::SurfaceHandle surface_ = 0;
    Meridian::UI::NifView::CameraState camera_{};
    RE::FormID selected_ = 0;
    bool layoutReady_ = false;
};
