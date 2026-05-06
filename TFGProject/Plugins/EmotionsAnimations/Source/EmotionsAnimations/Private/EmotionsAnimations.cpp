// Copyright Epic Games, Inc. All Rights Reserved.

#include "EmotionsAnimations.h"
#include "Misc/MessageDialog.h"
#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "HAL/PlatformProcess.h"

#define LOCTEXT_NAMESPACE "FEmotionsAnimationsModule"

void FEmotionsAnimationsModule::StartupModule()
{
#if PLATFORM_WINDOWS
	UE_LOG(LogTemp, Log, TEXT("EmotionsAnimations Plugin loaded"));
#else
	UE_LOG(LogTemp, Error, TEXT("EmotionsAnimations Plugin only support Windows"));
#endif // PLATFORM_WINDOWS
}

void FEmotionsAnimationsModule::ShutdownModule()
{
}

#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FEmotionsAnimationsModule, EmotionsAnimations)
