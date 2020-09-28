#include "FourdRecPlayer.h"
#include "Materials/MaterialInstanceDynamic.h"
#include <EngineGlobals.h>
#include "Modules/ModuleManager.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include <Runtime/Engine/Classes/Engine/Engine.h>
#define print(text) if (GEngine) GEngine->AddOnScreenDebugMessage(-1, 15, FColor::Yellow, text)


AFourdRecPlayer::AFourdRecPlayer()
{
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("root"));

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("4DMesh"));
	Mesh->SetupAttachment(RootComponent);

	PreviewMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PreviewMesh"));
	PreviewMesh->bHiddenInGame = true;
	PreviewMesh->SetupAttachment(RootComponent);
	UMaterialInterface* MeshMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("Material'/fourdrec/FourdRecMaterial.FourdRecMaterial'"));
	PreviewMatInst = PreviewMesh->CreateDynamicMaterialInstance(0, MeshMaterial);
	
	CurrentFrame = -1;
	bAutoPlayWhileCached = true;
	bLoop = true;
	bCachedCompleted = false;
	bDestroyWhileFinishPlay = false;
	PlaySpeed = 1;
	StartFrame = 0;
	Data = nullptr;

	PrimaryActorTick.bCanEverTick = true;

	DecodedTextureCount = 0;
	DecodeDelegate.BindUFunction(this, "OnDecodeCompleted");
}

void AFourdRecPlayer::BeginPlay()
{
	Super::BeginPlay();

	if (Data == nullptr)
	{
		UE_LOG(LogTemp, Fatal, TEXT("No data in player!!"));
		return;
	}

	CurrentFrame = StartFrame - 1;
	DecodedTextureCount = 0;
	Textures.Empty();
	bCachedCompleted = false;

	PerFrameDuration = 1 / Data->FPS * 1 / PlaySpeed;

	UMaterialInterface* MeshMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("Material'/fourdrec/FourdRecMaterial.FourdRecMaterial'"));
	MatInst = Mesh->CreateDynamicMaterialInstance(0, MeshMaterial);
	
	Data->LoadAssets(FStreamableDelegate::CreateUObject(this, &AFourdRecPlayer::OnAssetLoadCompleted));
}

void AFourdRecPlayer::BeginDestroy()
{
	Super::BeginDestroy();
	Mesh->SetStaticMesh(nullptr);
	Textures.Empty();
	if (Data != nullptr)
	{
		Data->UnloadAssets();
	}
}

void  AFourdRecPlayer::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
#if WITH_EDITOR
	if (Data != nullptr)
	{
		if (StartFrame < 0 || StartFrame >= Data->FrameCount)
		{
			PreviewMesh->SetStaticMesh(nullptr);
			return;
		}
		UStaticMesh* FrameMesh = Data->MeshPtrs[StartFrame].LoadSynchronous();
		PreviewMesh->SetStaticMesh(FrameMesh);
		static IImageWrapperModule* ImageWrapperModule = &FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
		const TArray<uint8>* Buffer = &Data->TexturePtr.LoadSynchronous()->ImageBuffers[StartFrame].Buffer;
		FImageDecodeResult Result = UImageDecoder::DecodeBuffer(this, Buffer, StartFrame, ImageWrapperModule);
		PreviewTexture = Result.Texture;
		PreviewMatInst->SetTextureParameterValue("FourdRecTexture", PreviewTexture);
		return;
	}
	PreviewMesh->SetStaticMesh(nullptr);
#endif
}

void AFourdRecPlayer::OnAssetLoadCompleted()
{
	DecodeTexture();
}

void AFourdRecPlayer::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	if (bPlaying)
	{
		TickDuration += DeltaTime;
		if (PerFrameDuration > 0 && TickDuration >= PerFrameDuration)
		{
			TickDuration -= PerFrameDuration;
			PlayNextFrame();
		}
	}
	else if (bCachedCompleted)
	{
		if (bAutoPlayWhileCached)
		{
			bPlaying = true;
		}
		else if (Mesh->GetStaticMesh() == nullptr)
		{
			DisplayFrame(CurrentFrame, false);
		}
	}
}

void AFourdRecPlayer::PlayNextFrame()
{
	if (!bCachedCompleted)
	{
		UE_LOG(LogTemp, Fatal, TEXT("Data haven't decoded."));
		return;
	}

	int32 NextFrame = CurrentFrame + 1;
	if (NextFrame >= Data->FrameCount || NextFrame < 0)
	{
		if (bLoop)
		{
			NextFrame = 0;
		}
		else
		{
			PerFrameDuration = 0;
			if (bDestroyWhileFinishPlay)
			{
				Destroy();
			}
			return;
		}
	}

	DisplayFrame(NextFrame, false);
}

void AFourdRecPlayer::DisplayFrame(const int32 FrameNumber, const bool CheckPlaying)
{
	if (bPlaying && CheckPlaying)
	{
		UE_LOG(LogTemp, Fatal, TEXT("Player is playing!!"));
		return;
	}

	if (!bCachedCompleted)
	{
		UE_LOG(LogTemp, Fatal, TEXT("Data haven't decoded."));
		return;
	}

	if (FrameNumber < 0 || FrameNumber >= Data->FrameCount)
	{
		UE_LOG(LogTemp, Fatal, TEXT("FrameNumber out of range!"));
		return;
	}

	CurrentFrame = FrameNumber;
	UTexture2D* Texture = Textures[CurrentFrame];
	MatInst->SetTextureParameterValue("FourdRecTexture", Texture);
	Mesh->SetStaticMesh(Data->MeshPtrs[CurrentFrame].Get());
}

void AFourdRecPlayer::DecodeTexture()
{
	Textures.AddUninitialized(Data->FrameCount);
	static IImageWrapperModule* ImageWrapperModule = &FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));

	for (int32 i = 0; i < Data->FrameCount; i++)
	{
		const TArray<uint8>* Buffer = &Data->TexturePtr.Get()->ImageBuffers[i].Buffer;
		UImageDecoder* Decoder = UImageDecoder::Create(this, Buffer, i, ImageWrapperModule);
		Decoder->OnDecodeCompleted().AddUnique(DecodeDelegate);
	}
}

void AFourdRecPlayer::OnDecodeCompleted(FImageDecodeResult Result)
{
	Textures[Result.Index] = Result.Texture;
	DecodedTextureCount += 1;

	if (DecodedTextureCount == Data->FrameCount)
	{
		bCachedCompleted = true;
	}
}