# Canvas Bot — Code Signing Guide

## Context
The Canvas Bot `.exe` triggers Windows SmartScreen warnings because it's unsigned. Purchasing a code signing certificate will remove the "Unknown Publisher" warning and build user trust. This guide covers the two practical options, the purchase/setup process, and how to integrate signing into the build workflow.

---

## Option A: Microsoft Artifact Signing (Recommended)

Formerly "Trusted Signing." Cloud-based, cheapest option, managed by Microsoft.

**Cost:** $9.99/month (Basic tier — 5,000 signatures/month)
**Pros:** Cheapest, no hardware token needed, Microsoft-managed HSM, Public Trust profiles eliminate SmartScreen warnings
**Cons:** Requires Azure subscription, more setup steps, relatively new service

### Setup Process

1. **Create an Azure account** at https://azure.microsoft.com (free tier is fine, Artifact Signing is billed separately)
2. **Register the resource provider:**
   ```
   az login
   az provider register --namespace Microsoft.CodeSigning
   ```
3. **Create an Artifact Signing account** in the Azure portal
4. **Complete identity validation** — choose "Individual" validation. Microsoft will verify your identity.
5. **Create a certificate profile** — select "Public Trust" (this is what removes SmartScreen warnings)
6. **Set up signing integration** — install the signing tools:
   ```
   dotnet tool install --global sign
   ```
7. **Sign your exe:**
   ```
   sign code azure-code-signing CanvasBot.exe ^
     --azure-key-vault-url <your-account-endpoint> ^
     --azure-key-vault-certificate <profile-name> ^
     --timestamp-url http://timestamp.acs.microsoft.com
   ```

**Documentation:** https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart

---

## Option B: Traditional CA Certificate (SSL.com)

Established process, works with standard `signtool`.

**Cost:** ~$250-400/year depending on provider and term
**Providers (cheapest to most expensive):**
- CheapSSLSecurity: ~$129/yr
- SignMyCode / SSL.com: ~$216-250/yr
- Sectigo: ~$280/yr
- DigiCert: ~$400+/yr

### Important: Hardware Key Requirement (since June 2023)

All code signing certificates now require FIPS 140-2 Level 2 key storage. You **cannot** get a downloadable `.pfx` file anymore. Options:
- **YubiKey 5 FIPS** (~$80 one-time) — USB hardware token, works offline with `signtool`
- **Cloud signing service** — SSL.com's eSigner, Sectigo's cloud HSM, etc. (usually included or small fee)

### Purchase Process (SSL.com Individual Validation)

1. Go to https://www.ssl.com/certificates/code-signing/
2. Select "Individual Validation (IV) Code Signing Certificate"
3. Complete purchase (~$250/yr)
4. **Identity validation** — submit:
   - Government-issued photo ID (front + back)
   - May require a video call verification
5. **Choose key storage:**
   - **eSigner (cloud)** — sign from any machine, no hardware needed, ~$20/mo extra
   - **YubiKey** — SSL.com ships a pre-configured YubiKey, or you provide your own FIPS-compliant one
6. Certificate is issued (typically 1-3 business days after validation)

### Signing with signtool (YubiKey or .pfx)

Install Windows SDK (for `signtool`):
```
winget install Microsoft.WindowsSDK
```

Sign the PyInstaller output:
```
signtool sign /sha1 <THUMBPRINT> /tr http://timestamp.sectigo.com /td sha256 /fd sha256 CanvasBot.exe
```

Or with eSigner cloud signing:
```
signtool sign /fd sha256 /tr http://ts.ssl.com /td sha256 /sha1 <THUMBPRINT> CanvasBot.exe
```

---

## SmartScreen Reputation (Important)

As of March 2024, **neither OV nor EV certificates provide instant SmartScreen bypass.** Both certificate types now build reputation organically through user downloads. This means:

- The first few users may still see a SmartScreen warning even with a signed exe
- Reputation builds as more users download and run the application
- After enough installs, SmartScreen stops warning
- Signing still shows your verified name instead of "Unknown Publisher", which is a major trust signal

---

## Integration with Build Workflow

### Sign After PyInstaller Build

PyInstaller doesn't sign natively. Sign the output exe after building:

```powershell
# Build
pyinstaller canvas_bot.spec

# Sign
signtool sign /sha1 <THUMBPRINT> /tr http://timestamp.sectigo.com /td sha256 /fd sha256 dist/CanvasBot.exe

# Verify
signtool verify /pa dist/CanvasBot.exe
```

### Release Checklist Integration

See `claude/RELEASE_CHECKLIST.md` — the optional signing step should be updated with the actual command for whichever option you choose.

---

## Recommendation

**Microsoft Artifact Signing** is the best value at $9.99/month ($120/year) with no hardware token needed. It's newer and has more setup friction, but once configured it's straightforward. If you prefer a traditional CA and want to sign offline (no cloud dependency), get an **SSL.com IV certificate with a YubiKey**.