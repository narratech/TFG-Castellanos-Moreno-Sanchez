// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "OneHotEncoder.generated.h"


UCLASS()
class MBTI_MOTION_API UOneHotEncoder : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:

	UFUNCTION(BlueprintCallable, Category = "EmotionAI")
	static TArray<float> OneHotEncodeWithCategories(
		const FString& Input,
		const TArray<FString>& Categories
	);

	UFUNCTION(BlueprintCallable, Category = "EmotionAI")
	static FString OneHotDecodeWithCategories(
		const TArray<float>& Input,
		const TArray<FString>& Categories
	);
};
