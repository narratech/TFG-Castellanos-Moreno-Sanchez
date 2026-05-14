// Copyright Epic Games, Inc. All Rights Reserved.

using System.IO;
using UnrealBuildTool;

public class MBTI_Motion : ModuleRules
{
	public MBTI_Motion(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
		
		PublicIncludePaths.AddRange(
			new string[] {
				// ... add public include paths required here ...
			}
			);
				
		
		PrivateIncludePaths.AddRange(
			new string[] {
				// ... add other private include paths required here ...
			}
			);


        // Ruta de ONNX
        string ONNXPath = Path.Combine(ModuleDirectory, "../ThirdParty/ONNXRuntime");

        //Includes
        PublicIncludePaths.Add(Path.Combine(ONNXPath, "include"));

        //Static libraries
        PublicAdditionalLibraries.Add(Path.Combine(ONNXPath, "lib", "onnxruntime.lib"));


        //Dynamic libraries
        PublicDelayLoadDLLs.Add("onnxruntime.dll");
        RuntimeDependencies.Add(Path.Combine("$(PluginDir)/Binaries/Win64/onnxruntime.dll"));


        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "Projects",
                "CoreUObject",
                "Engine",
                "InputCore"
				// ... add other public dependencies that you statically link with here ...
			}
            );


        PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"CoreUObject",
				"Engine",
				"Slate",
				"SlateCore",
				// ... add private dependencies that you statically link with here ...	
			}
			);
		
		
		DynamicallyLoadedModuleNames.AddRange(
			new string[]
			{
				// ... add any modules that your module loads dynamically here ...
			}
			);
	}
}
