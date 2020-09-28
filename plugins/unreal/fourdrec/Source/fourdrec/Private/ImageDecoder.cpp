#include "ImageDecoder.h"
#include "Modules/ModuleManager.h"
#include "IImageWrapper.h"
#include "Async.h"


FImageDecodeResult::FImageDecodeResult()
{
	Texture = nullptr;
	Index = -1;
}

FImageDecodeResult::FImageDecodeResult(UTexture2D* InTexture, int32 InIndex)
{
	Texture = InTexture;
	Index = InIndex;
}


UImageDecoder* UImageDecoder::Create(UObject* Outer, const TArray<uint8>* ImageBuffer, int32 Index, IImageWrapperModule* ImageWrapperModule)
{
	UImageDecoder* Decoder = NewObject<UImageDecoder>();
	Decoder->StartDecodeAsync(Outer, ImageBuffer, Index, ImageWrapperModule);
	return Decoder;
}


void UImageDecoder::StartDecodeAsync(UObject* Outer, const TArray<uint8>* ImageBuffer, int32 Index, IImageWrapperModule* ImageWrapperModule)
{
	Future = Async(EAsyncExecution::ThreadPool, [=]() { return DecodeBuffer(Outer, ImageBuffer, Index, ImageWrapperModule); }, [this]()
	{
		if (Future.IsValid())
		{
			AsyncTask(ENamedThreads::GameThread, [this]() { DecodeCompleted.Broadcast(Future.Get()); });
		}
	});
}


FImageDecodeResult UImageDecoder::DecodeBuffer(
	UObject* Outer, const TArray<uint8>* ImageBuffer, int32 Index, IImageWrapperModule* ImageWrapperModule)
{
	TSharedPtr<IImageWrapper> ImageWrapper = ImageWrapperModule->CreateImageWrapper(EImageFormat::JPEG);
	const TArray<uint8>* DecompressedImageData;
	ImageWrapper->SetCompressed(ImageBuffer->GetData(), ImageBuffer->Num());
	bool Success = ImageWrapper->GetRaw(ERGBFormat::BGRA, 8, DecompressedImageData);

	int32 TextureWidth = ImageWrapper->GetWidth();
	int32 TextureHeight = ImageWrapper->GetHeight();

	FName AssetName = MakeUniqueObjectName(Outer, UTexture2D::StaticClass(), "texture");

	UTexture2D* FourdTexture = NewObject<UTexture2D>(Outer, AssetName, RF_Transient);

	FourdTexture->PlatformData = new FTexturePlatformData();
	FourdTexture->PlatformData->SizeX = TextureWidth;
	FourdTexture->PlatformData->SizeY = TextureHeight;
	FourdTexture->PlatformData->NumSlices = 1;
	FourdTexture->PlatformData->PixelFormat = EPixelFormat::PF_B8G8R8A8;

	FTexture2DMipMap* Mip = new FTexture2DMipMap();
	FourdTexture->PlatformData->Mips.Add(Mip);
	Mip->SizeX = TextureWidth;
	Mip->SizeY = TextureHeight;
	Mip->BulkData.Lock(LOCK_READ_WRITE);
	void* FourdTextureBuffer = Mip->BulkData.Realloc(DecompressedImageData->Num());
	FMemory::Memcpy(FourdTextureBuffer, DecompressedImageData->GetData(), DecompressedImageData->Num());
	Mip->BulkData.Unlock();

	FourdTexture->UpdateResource();

	FImageDecodeResult Result = FImageDecodeResult(FourdTexture, Index);
	return Result;
}