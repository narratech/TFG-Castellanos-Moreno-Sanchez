// Copyright Epic Games, Inc. All Rights Reserved.

#include "MBTI_Motion.h"

#define LOCTEXT_NAMESPACE "FMBTI_MotionModule"

void FMBTI_MotionModule::StartupModule()
{
#if PLATFORM_WINDOWS
	UE_LOG(LogTemp, Log, TEXT("MBTI Motion Plugin loaded"));
#else
	UE_LOG(LogTemp, Error, TEXT("MBTI Motion Plugin only support Windows"));
#endif // PLATFORM_WINDOWS
}

void FMBTI_MotionModule::ShutdownModule()
{
}


#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FMBTI_MotionModule, MBTI_Motion)