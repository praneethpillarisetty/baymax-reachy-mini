# LiteRT model integration

1. Obtain an exact, licensed artifact explicitly; never download during startup.
2. Verify its LiteRT runtime/version, target architecture, tokenizer and conversion recipe.
3. Copy the example profile and fully declare identifiers, paths, named signatures, quantization, measured memory, context, and platform.
4. Implement a profile-specific runner that tokenizes, binds tensors, decodes, and returns the documented JSON contract.
5. Unit-test signatures and benchmark on the target. The generic adapter refuses missing files and refuses inference without a runner.
