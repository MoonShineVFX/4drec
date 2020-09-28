#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Engine/StaticMesh.h"
#include "ImageDecoder.h"
#include "FourdRecData.h"
#include "FourdRecPlayer.generated.h"


UCLASS()
class FOURDREC_API AFourdRecPlayer : public AActor
{
	GENERATED_BODY()
	
public:
	AFourdRecPlayer();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaTime) override;
	virtual void BeginDestroy() override;
	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
		UFourdRecData* Data;

	UPROPERTY(EditInstanceOnly)
		int32 StartFrame;

	UPROPERTY(EditInstanceOnly, BlueprintReadOnly)
		bool bAutoPlayWhileCached;

	UPROPERTY(EditInstanceOnly, BlueprintReadOnly, meta = (EditCondition = "!bDestroyWhileFinishPlay"))
		bool bLoop;

	UPROPERTY(EditInstanceOnly, BlueprintReadOnly)
		float PlaySpeed;

	UPROPERTY(EditInstanceOnly, BlueprintReadOnly, meta = (EditCondition = "!bLoop"))
		bool bDestroyWhileFinishPlay;

	UPROPERTY(BlueprintReadOnly, Transient)
		bool bCachedCompleted;

	UPROPERTY(BlueprintReadOnly, Transient)
		int32 CurrentFrame;

	UPROPERTY(BlueprintReadOnly)
		bool bPlaying;

	UFUNCTION(BlueprintCallable)
		void PlayNextFrame();

	UFUNCTION(BlueprintCallable, meta = (HidePin = "CheckPlaying"))
		void DisplayFrame(const int32 FrameNumber, const bool CheckPlaying = true);

	void OnAssetLoadCompleted();

	void DecodeTexture();

	UPROPERTY(BlueprintReadOnly, Transient)
		int32 DecodedTextureCount;

private:
	UPROPERTY(Transient)
		UStaticMeshComponent* Mesh;

	UPROPERTY(Transient)
		UMaterialInstanceDynamic* MatInst;

	UPROPERTY(Transient)
		TArray<UTexture2D*> Textures;

	UPROPERTY(Transient)
		UStaticMeshComponent* PreviewMesh;

	UPROPERTY(Transient)
		UMaterialInstanceDynamic* PreviewMatInst;

	UPROPERTY(Transient)
		UTexture2D* PreviewTexture;

	UPROPERTY()
		float TickDuration;

	UPROPERTY()
		float PerFrameDuration;

	FScriptDelegate DecodeDelegate;

	UFUNCTION()
		void OnDecodeCompleted(FImageDecodeResult Result);
};
