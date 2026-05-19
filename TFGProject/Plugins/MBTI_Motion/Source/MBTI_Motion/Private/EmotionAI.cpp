#include "EmotionAI.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "onnxruntime_c_api.h"
#include "HAL/PlatformProcess.h"
#include "Windows/WindowsHWrapper.h" // para LoadLibraryEx
#include "Windows/AllowWindowsPlatformTypes.h"
#include <vector>
#include "Interfaces/IPluginManager.h"

//Version de ORT que se va a usar
#define ORT_VERSION 20

struct FEmotionIAInternalModel
{
    TArray<uint8> ModelBuffer;
    OrtEnv* Env = nullptr;
    OrtSessionOptions* SessionOptions = nullptr;
    OrtSession* Session = nullptr;

    ~FEmotionIAInternalModel()
    {
        const OrtApi* Api = OrtGetApiBase()->GetApi(ORT_VERSION);
        if (Session) { Api->ReleaseSession(Session); Session = nullptr; }
        if (SessionOptions) { Api->ReleaseSessionOptions(SessionOptions); SessionOptions = nullptr; }
        if (Env) { Api->ReleaseEnv(Env); Env = nullptr; }
    }
};

bool UEmotionAI::CheckONNXDependenciesDynamic()
{
    if (IPluginManager::Get().FindPlugin("MBTI_Motion") == nullptr) {
        UE_LOG(LogTemp, Error, TEXT("No se pudo encontrar la ruta del plugin MBTI_Motion"));
        return false;
    }
    FString BasePath = IPluginManager::Get().FindPlugin("MBTI_Motion")->GetBaseDir() / TEXT("/Binaries/Win64");
    FString MainDLL = BasePath / TEXT("onnxruntime.dll");

    // Intentamos cargar la DLL principal sin ejecutar DllMain
    HMODULE MainHandle = LoadLibraryExW(*MainDLL, nullptr, LOAD_LIBRARY_AS_IMAGE_RESOURCE);
    if (!MainHandle)
    {
        UE_LOG(LogTemp, Error, TEXT("No se pudo cargar la DLL principal: %s"), *MainDLL);
        return false;
    }

    // Si llegamos aquí, podemos usar Dependency Walker / DumpBin para inspeccionar dependencias reales.
    // Alternativa manual: verificar DLL comunes (MSVC runtimes) como antes:
    TArray<FString> CommonDependencies = {
        TEXT("KERNEL32.dll"),
        TEXT("ADVAPI32.dll"),
        TEXT("MSVCP140.dll"),
        TEXT("MSVCP140_1.dll"),
        TEXT("api-ms-win-core-path-l1-1-0.dll"),
        TEXT("dbghelp.dll"),
        TEXT("SETUPAPI.dll"),
        TEXT("dxgi.dll"),
        TEXT("VCRUNTIME140_1.dll"),
        TEXT("VCRUNTIME140.dll"),
        TEXT("api-ms-win-crt-heap-l1-1-0.dll"),
        TEXT("api-ms-win-crt-runtime-l1-1-0.dll"),
        TEXT("api-ms-win-crt-convert-l1-1-0.dll"),
        TEXT("api-ms-win-crt-stdio-l1-1-0.dll"),
        TEXT("api-ms-win-crt-string-l1-1-0.dll"),
        TEXT("api-ms-win-crt-time-l1-1-0.dll"),
        TEXT("api-ms-win-crt-filesystem-l1-1-0.dll"),
        TEXT("api-ms-win-crt-locale-l1-1-0.dll"),
        TEXT("api-ms-win-crt-math-l1-1-0.dll")
    };

    bool bAllLoaded = true;

    for (const FString& Dep : CommonDependencies)
    {
        HMODULE Handle = LoadLibraryW(*Dep);
        if (!Handle)
        {
            UE_LOG(LogTemp, Error, TEXT("Falta DLL dependiente: %s"), *Dep);
            bAllLoaded = false;
        }
    }

    // Liberamos la DLL principal
    FreeLibrary(MainHandle);

    if (!bAllLoaded)
    {
        UE_LOG(LogTemp, Error, TEXT("No todas las dependencias están presentes."));
        return false;
    }

    return true;
}

bool UEmotionAI::InitModel()
{
    // Lista de DLLs que normalmente necesita ONNX Runtime C API
    if (!CheckONNXDependenciesDynamic()) {
        return false;
    }

    // Paso 1: Crear InternalModel
    InternalModel = new FEmotionIAInternalModel();
    if (!InternalModel)
    {
        UE_LOG(LogTemp, Error, TEXT("No se pudo crear InternalModel"));
        return false;
    }

    // Paso 2: Cargar modelo desde disco
    TArray<uint8> Buffer;
    FString FullPath = FPaths::Combine(FPaths::ProjectContentDir(), ModelPath);

    if (!FFileHelper::LoadFileToArray(Buffer, *FullPath) || Buffer.Num() == 0)
    {
        UE_LOG(LogTemp, Error, TEXT("Modelo no encontrado o vacío en %s"), *FullPath);
        delete InternalModel;
        InternalModel = nullptr;
        return false;
    }

    InternalModel->ModelBuffer = Buffer;

    // Paso 3: Obtener API de ONNX Runtime
    const OrtApiBase* Base = OrtGetApiBase();

    if (!Base)
    {
        UE_LOG(LogTemp, Error, TEXT("OrtGetApiBase devolvió NULL"));
        delete InternalModel;
        InternalModel = nullptr;
        return false;
    }

    const OrtApi* Api = Base->GetApi(ORT_VERSION);

    if (!Api)
    {
        UE_LOG(LogTemp, Error, TEXT("GetApi devolvió NULL"));
        delete InternalModel;
        InternalModel = nullptr;
        return false;
    }

    // Paso 4: Crear Env
    OrtStatus* Status = Api->CreateEnv(ORT_LOGGING_LEVEL_WARNING, "EmotionAI", &InternalModel->Env);
    if (Status)
    {
        UE_LOG(LogTemp, Error, TEXT("Error creando OrtEnv"));
        delete InternalModel;
        InternalModel = nullptr;
        return false;
    }

    // Paso 5: Crear SessionOptions
    Status = Api->CreateSessionOptions(&InternalModel->SessionOptions);
    if (Status)
    {
        UE_LOG(LogTemp, Error, TEXT("Error creando SessionOptions"));
        delete InternalModel;
        InternalModel = nullptr;
        return false;
    }

    Api->SetIntraOpNumThreads(InternalModel->SessionOptions, 1);
    Api->SetSessionGraphOptimizationLevel(InternalModel->SessionOptions, ORT_ENABLE_EXTENDED);

    const wchar_t* ModelPathW = *FullPath;
    // Paso 6: Crear Session desde el buffer en memoria
    Status = Api->CreateSession(
        InternalModel->Env,
        ModelPathW,
        InternalModel->SessionOptions,
        &InternalModel->Session
    );

    if (Status != nullptr)
    {
        const char* ErrorMsg = Api->GetErrorMessage(Status);

        UE_LOG(
            LogTemp,
            Error,
            TEXT("Error creando OrtSession desde memoria: %s"),
            ANSI_TO_TCHAR(ErrorMsg)
        );

        Api->ReleaseStatus(Status);

        delete InternalModel;
        InternalModel = nullptr;
        return false;
    }

    return true;
}

void UEmotionAI::AddTimeStep(const TArray<float>& InputData) {

    if (InputData.Num() != FeatureSize)
    {
        UE_LOG(LogTemp, Error, TEXT("InputData incorrecto: el input fue de tamaño %d, se esperaba %d"), InputData.Num(), FeatureSize);
        return;
    }

    // Sobreescribir la ultima entrada registrada
    for (int i = CircularIndex * FeatureSize; i < (CircularIndex + 1) * FeatureSize; i++) {
        InputSequence[i] = InputData[i % FeatureSize];
    }
}

void UEmotionAI::ChangeTimeStepsTable(const TArray<float>& InputData) {
    if (InputData.Num() != FeatureSize * SequenceLength)
    {
        UE_LOG(LogTemp, Error, TEXT("InputData incorrecto: el input fue de tamaño %d, se esperaba %d"), InputData.Num(), FeatureSize * SequenceLength);
        return;
    }

    FMemory::Memcpy(
        InputSequence.GetData(),
        InputData.GetData(),
        FeatureSize * SequenceLength * sizeof(float)
    );

    CircularIndex = 0;

    /*for (int32 i = 0; i < SequenceLength; ++i) {
        for (int32 j = 0; j < FeatureSize; ++j) {
            UE_LOG(LogTemp, Log, TEXT("InputSequence %d: %f\n"), i, InputSequence[i * FeatureSize + j]);
        }
        UE_LOG(LogTemp, Log, TEXT("-----------------------------\n"));
    }*/
}

TMap<FString, float> UEmotionAI::RunInference()
{
    TMap<FString, float> Output;

    if (!InternalModel || !InternalModel->Session)
    {
        UE_LOG(LogTemp, Error, TEXT("Modelo no inicializado"));
        return Output;
    }

    //Obtener la API de Ort
    const OrtApi* Api = OrtGetApiBase()->GetApi(ORT_VERSION);
    OrtStatus* status;

    // Crear MemoryInfo para CPU
    OrtMemoryInfo* MemoryInfo = nullptr;
    status = Api->CreateCpuMemoryInfo(OrtArenaAllocator, OrtMemTypeDefault, &MemoryInfo);

    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseMemoryInfo(MemoryInfo);
        Api->ReleaseStatus(status);
        return Output;
    }


    for (int32 i = 0; i < SequenceLength; ++i)
    {
        // índice en InputSequence (circular buffer)
        int32 SrcIndex = ((CircularIndex - i + SequenceLength) % SequenceLength) * FeatureSize;

        // copiar a LinearInput en orden temporal correcto
        FMemory::Memcpy(
            LinearInput.GetData() + (SequenceLength - 1 - i) * FeatureSize,
            InputSequence.GetData() + SrcIndex,
            FeatureSize * sizeof(float)
        );
    }

    /*for (int32 i = 0; i < SequenceLength; ++i) {
        for (int32 j = 0; j < FeatureSize; ++j) {
            UE_LOG(LogTemp, Log, TEXT("InputSequence %d: %f\n"), i, LinearInput[i*FeatureSize+j]);
        }
        UE_LOG(LogTemp, Log, TEXT("-----------------------------\n"));
    }*/

    // Forma del tensor
    TArray<int64> InputShape = { 1, SequenceLength, FeatureSize };

    // Crear tensor de entrada con los datos de InputData
    OrtValue* InputTensor = nullptr;
    status = Api->CreateTensorWithDataAsOrtValue(
        MemoryInfo,
        LinearInput.GetData(),
        LinearInput.Num() * sizeof(float),
        InputShape.GetData(),
        InputShape.Num(),
        ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,      // Tipo
        &InputTensor
    );

    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseValue(InputTensor);
        Api->ReleaseMemoryInfo(MemoryInfo);
        Api->ReleaseStatus(status);
        return Output;
    }

    // Nombres de input/output
    OrtAllocator* Alloc = nullptr;
    status = Api->GetAllocatorWithDefaultOptions(&Alloc);

    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseValue(InputTensor);
        Api->ReleaseMemoryInfo(MemoryInfo);
        Api->ReleaseStatus(status);
        return Output;
    }

    char* InputTensorName = nullptr;
    status = Api->SessionGetInputName(InternalModel->Session, 0, Alloc, &InputTensorName);

    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->AllocatorFree(Alloc, InputTensorName);
        Api->ReleaseValue(InputTensor);
        Api->ReleaseMemoryInfo(MemoryInfo);
        Api->ReleaseStatus(status);
        return Output;
    }

    char* OutputTensorName = nullptr;
    status = Api->SessionGetOutputName(InternalModel->Session, 0, Alloc, &OutputTensorName);

    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->AllocatorFree(Alloc, InputTensorName);
        Api->AllocatorFree(Alloc, OutputTensorName);
        Api->ReleaseValue(InputTensor);
        Api->ReleaseMemoryInfo(MemoryInfo);
        Api->ReleaseStatus(status);
        return Output;
    }

    // Run
    const char* InputTensorNames[] = { InputTensorName };
    const char* OutputTensorNames[] = { OutputTensorName };
    OrtValue* OutputTensors[1] = { nullptr };

    Api->AllocatorFree(Alloc, InputTensorName);
    Api->AllocatorFree(Alloc, OutputTensorName);

    status = Api->Run(
        InternalModel->Session,
        nullptr,             // RunOptions
        InputTensorNames,
        &InputTensor,
        1,                   // num_inputs
        OutputTensorNames,
        1,                   // num_outputs
        OutputTensors
    );

    Api->ReleaseValue(InputTensor);

    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseValue(OutputTensors[0]);
        Api->ReleaseMemoryInfo(MemoryInfo);
        Api->ReleaseStatus(status);
        return Output;
    }

    if (OutputTensors[0] == NULL) {
        UE_LOG(LogTemp, Error, TEXT("Output tensor es NULL"));
        Api->ReleaseValue(OutputTensors[0]);
        Api->ReleaseMemoryInfo(MemoryInfo);
        Api->ReleaseStatus(status);
        return Output;
    }

    // Obtener datos de salida
    float* FloatArray = nullptr;

    status = Api->GetTensorMutableData(OutputTensors[0], (void**)&FloatArray);

    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseValue(OutputTensors[0]);
        Api->ReleaseMemoryInfo(MemoryInfo);
        Api->ReleaseStatus(status);
        return Output;
    }

    if (OutputNames.Num() != OutputSize) {
        UE_LOG(LogTemp, Error, TEXT("OutputSize error: output size es %d, se esperaba %d"), OutputSize, OutputNames.Num());
    }

    for (int i = 0; i < OutputSize; i++)
    {
        Output.Add(OutputNames[i], FloatArray[i]);
    }

    Api->ReleaseValue(OutputTensors[0]);

    // Liberar memoria temporal
    Api->ReleaseMemoryInfo(MemoryInfo);
    Api->ReleaseStatus(status);

    CircularIndex++;
    if (CircularIndex == SequenceLength)
        CircularIndex = 0;

    return Output;
}

void UEmotionAI::BeginDestroy()
{
    if (InternalModel)
    {
        delete InternalModel;
        InternalModel = nullptr;
    }

    Super::BeginDestroy();
}

void UEmotionAI::BeginPlay()
{
    Super::BeginPlay();

    if (ModelPath.IsEmpty())
    {
        UE_LOG(LogTemp, Error, TEXT("EmotionIA: ModelPath no está configurado"));
        return;
    }

    if (!InitModel())
    {
        UE_LOG(LogTemp, Error, TEXT("EmotionIA: No se pudo inicializar el modelo"));
        return;
    }

    CircularIndex = 0;

    OrtStatus* status;
    const OrtApi* Api = OrtGetApiBase()->GetApi(ORT_VERSION);
    OrtTypeInfo* type_info = NULL;

    status = Api->SessionGetInputTypeInfo(
        InternalModel->Session,
        0, // índice de input
        &type_info
    );

    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseTypeInfo(type_info);
        Api->ReleaseStatus(status);
        return;
    }

    const OrtTensorTypeAndShapeInfo* tensor_info;
    status = Api->CastTypeInfoToTensorInfo(type_info, &tensor_info);
    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseTypeInfo(type_info);
        Api->ReleaseStatus(status);
        return;
    }
    int64_t dims[3];
    status = Api->GetDimensions(tensor_info, dims, 3);
    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseTypeInfo(type_info);
        Api->ReleaseStatus(status);
        return;
    }

    // dims[0] = batch
    // dims[1] = sequence_length
    // dims[2] = input_size

    SequenceLength = dims[1];
    FeatureSize = dims[2];

    InputSequence.Init(0, FeatureSize * SequenceLength);
    LinearInput.Init(0, FeatureSize * SequenceLength);

    status = Api->SessionGetOutputTypeInfo(
        InternalModel->Session,
        0, // índice del output
        &type_info
    );
    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseTypeInfo(type_info);
        Api->ReleaseStatus(status);
        return;
    }

    status = Api->CastTypeInfoToTensorInfo(type_info, &tensor_info);
    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseTypeInfo(type_info);
        Api->ReleaseStatus(status);
        return;
    }

    size_t size;
    status = Api->GetTensorShapeElementCount(tensor_info, &size);
    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseTypeInfo(type_info);
        Api->ReleaseStatus(status);
        return;
    }

    OutputSize = size;

    // Allocator
    OrtAllocator* Allocator = nullptr;
    Api->GetAllocatorWithDefaultOptions(&Allocator);

    // Metadata
    OrtModelMetadata* Metadata = nullptr;
    status = Api->SessionGetModelMetadata(
        InternalModel->Session,
        &Metadata
    );

    if (status != NULL) {
        const char* errorMsg = Api->GetErrorMessage(status);
        FString UnrealError = UTF8_TO_TCHAR(errorMsg);
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: %s"), *UnrealError);
        Api->ReleaseTypeInfo(type_info);
        Api->ReleaseStatus(status);
        return;
    }

    Api->ReleaseTypeInfo(type_info);

    // Leer clave "output_names"
    char* value = nullptr;

    status = Api->ModelMetadataLookupCustomMetadataMap(
        Metadata,
        Allocator,
        "output_names",
        &value
    );

    if (status != NULL || value == nullptr) {
        UE_LOG(LogTemp, Error, TEXT("Onnx run error: no se pudo leer output_names de los metadatos"));
        Api->ReleaseStatus(status);
        Api->AllocatorFree(Allocator, value);
        Api->ReleaseModelMetadata(Metadata);
        return;
    }

    FString NamesString = UTF8_TO_TCHAR(value);

    // Separar por comas → TArray<FString>
    NamesString.ParseIntoArray(OutputNames, TEXT(","), true);

    for (const FString& Name : OutputNames)
    {
        UE_LOG(LogTemp, Warning, TEXT("Output: %s"), *Name);
    }

    Api->AllocatorFree(Allocator, value);
    Api->ReleaseModelMetadata(Metadata);
}