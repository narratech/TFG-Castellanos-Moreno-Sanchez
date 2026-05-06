#pragma once

#include "CoreMinimal.h"

#include "EmotionAI.generated.h"

struct FEmotionIAInternalModel;

UCLASS(ClassGroup = (AI), meta = (BlueprintSpawnableComponent))
class EMOTIONSANIMATIONS_API UEmotionAI : public UActorComponent
{
    GENERATED_BODY()

public:

    UFUNCTION(BlueprintCallable, Category = "EmotionAI")
    bool InitModel();

    UFUNCTION(BlueprintCallable, Category = "EmotionAI")
    TMap<FString, float> RunInference();

    UFUNCTION(BlueprintCallable, Category = "EmotionAI")
    void AddTimeStep(const TArray<float>& InputData);

    UFUNCTION(BlueprintCallable, Category = "EmotionAI")
    void ChangeTimeStepsTable(const TArray<float>& InputData);

protected:

    virtual void BeginDestroy() override;
    virtual void BeginPlay() override;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "EmotionAI")
    FString ModelPath;

private:

    FEmotionIAInternalModel* InternalModel = nullptr;

    bool CheckONNXDependenciesDynamic();

    TArray<float> InputSequence;

    int64 CircularIndex;

    TArray<float> LinearInput;

    int64_t SequenceLength = 0;

    int64_t FeatureSize = 0;

    int64_t OutputSize;

    TArray<FString> OutputNames;
};