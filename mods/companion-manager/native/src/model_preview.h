#pragma once

#include "MeridianUIAPI/NifViewDllLoader.h"
#include "MeridianUIAPI/RenderLayerDllLoader.h"
#include <nlohmann/json.hpp>
#include <cmath>

// Item model preview for the wear page. Every method runs on Skyrim's task thread, like the rest
// of the manager, and the panel only ever asks for an armor record it already listed.
class ModelPreview
{
public:
    void Initialize(Meridian::UI::Settings& settings)
    {
        layers_ = Meridian::UI::RenderLayer::Query(&settings, "CompanionManager");
        models_ = Meridian::UI::NifView::Query(&settings, "CompanionManager");
        if (!Available())
            logger::warn("Model preview unavailable: Meridian RenderLayer={} NifView={}",
                         layers_ ? "ok" : "missing", models_ ? "ok" : "missing");
    }

    bool Available() const { return layers_ && models_; }

    void Clear()
    {
        if (surface_ && Available())
        {
            layers_->SetVisible(surface_, false);
            models_->ClearModel(surface_);
        }
        selected_ = 0;
        layoutReady_ = false;
    }

    // The armor model comes from the follower's own sex, so a male-only or female-only mesh still
    // previews correctly; anything without a world model reports unsupported.
    void Select(RE::FormID actorID, RE::FormID itemID)
    {
        Clear();
        if (!Available())
            return;
        auto* actor = RE::TESForm::LookupByID<RE::Actor>(actorID);
        auto* item = RE::TESForm::LookupByID<RE::TESBoundObject>(itemID);
        auto* armor = item ? item->As<RE::TESObjectARMO>() : nullptr;
        if (!actor || !armor)
            return;
        const auto* base = actor->GetActorBase();
        const auto sex = base && base->GetSex() == RE::SEX::kFemale ? 1 : 0;
        const char* path = armor->worldModels[sex].GetModel();
        if (!path || !*path)
            path = armor->worldModels[1 - sex].GetModel();
        if (!path || !*path)
            return;
        if (!surface_)
        {
            Meridian::UI::RenderLayer::SurfaceCreateInfo info{};
            info.ownerName = "companion-manager";
            info.surfaceName = "wear-preview";
            // Only covers the dedicated empty viewport in the wear page; the list and the
            // attributes stay outside it and keep working as ordinary HTML.
            info.zOrder = 100;
            surface_ = layers_->CreateSurface(&info);
        }
        if (!surface_)
            return;
        camera_ = {};
        Meridian::UI::NifView::NifLoadInfo load{};
        load.surface = surface_;
        load.modelPath = path;
        if (models_->LoadModel(&load))
        {
            selected_ = itemID;
            path_ = path;
            models_->SetCamera(surface_, &camera_);
            logger::info("Wear preview requested: actor={:08X} item={:08X} {}", actorID, itemID, path);
        }
    }

    void Layout(const nlohmann::json& request)
    {
        if (!surface_ || !Available())
            return;
        const auto x = request.value("x", -1);
        const auto y = request.value("y", -1);
        const auto w = request.value("width", 0);
        const auto h = request.value("height", 0);
        layoutReady_ = x >= 0 && y >= 0 && w > 0 && h > 0 &&
            x <= 16384 && y <= 16384 && w <= 8192 && h <= 8192 &&
            layers_->SetRect(surface_, x, y, w, h);
        if (!layoutReady_)
            layers_->SetVisible(surface_, false);
    }

    void Camera(const nlohmann::json& request)
    {
        if (!surface_ || !Available())
            return;
        const auto yaw = request.value("yaw", 35.0f);
        const auto pitch = request.value("pitch", 15.0f);
        const auto distance = request.value("distance", 1.0f);
        if (!std::isfinite(yaw) || !std::isfinite(pitch) || !std::isfinite(distance))
            return;
        camera_.yawDegrees = std::fmod(yaw, 360.0f);
        camera_.pitchDegrees = std::clamp(pitch, -85.0f, 85.0f);
        camera_.distanceScale = std::clamp(distance, 0.25f, 4.0f);
        models_->SetCamera(surface_, &camera_);
    }

    // "unavailable" is the extension being missing, "unsupported" is nothing being loaded for this
    // item; the page shows a different message for each.
    const char* Status(RE::FormID itemID, bool focused)
    {
        if (!Available())
            return "unavailable";
        if (!surface_ || !itemID || itemID != selected_)
            return "unsupported";
        const auto status = models_->GetStatus(surface_);
        using Status = Meridian::UI::NifView::Status;
        layers_->SetVisible(surface_, focused && layoutReady_ && status == Status::Ready);
        // A failure here is usually the renderer rather than the file, so name both in the log; the
        // MeridianUI.log carries the renderer-side detail next to this message.
        if (status == Status::Failed && failedLogged_ != itemID)
        {
            failedLogged_ = itemID;
            logger::warn("Wear preview failed: item={:08X} path={} (see MeridianUI.log for the renderer's reason)",
                         itemID, path_);
        }
        switch (status)
        {
        case Status::Loading:
            return "loading";
        case Status::Ready:
            return "ready";
        case Status::Failed:
            return "failed";
        default:
            return "unsupported";
        }
    }

private:
    Meridian::UI::RenderLayer::IRenderLayerAPI* layers_ = nullptr;
    Meridian::UI::NifView::INifViewAPI* models_ = nullptr;
    Meridian::UI::RenderLayer::SurfaceHandle surface_ = 0;
    Meridian::UI::NifView::CameraState camera_{};
    RE::FormID selected_ = 0;
    RE::FormID failedLogged_ = 0;
    std::string path_;
    bool layoutReady_ = false;
};
