// SkillPM - GPG Signing and Verification
// Author: Bogdan Ticu
// License: MIT
//
// Provides key generation, manifest signing, and signature verification
// for skill packages. Authors sign their skill.yaml manifests to prove
// authenticity. The registry stores author public keys for verification.

package gpg

import (
	"bytes"
	"crypto"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/ProtonMail/go-crypto/openpgp"
	"github.com/ProtonMail/go-crypto/openpgp/armor"
	"github.com/ProtonMail/go-crypto/openpgp/packet"
	"github.com/skillpm/skillpm/pkg/config"
)

// GetKeyDir returns the directory where GPG keys are stored.
func GetKeyDir() (string, error) {
	cfgDir, err := config.GetConfigDir()
	if err != nil {
		return "", err
	}
	keyDir := filepath.Join(cfgDir, "gpg")
	os.MkdirAll(keyDir, 0700)
	return keyDir, nil
}

// GetSecretKeyPath returns the path to the user's private key.
func GetSecretKeyPath() (string, error) {
	keyDir, err := GetKeyDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(keyDir, "secret.asc"), nil
}

// GetPublicKeyPath returns the path to the user's public key.
func GetPublicKeyPath() (string, error) {
	keyDir, err := GetKeyDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(keyDir, "public.asc"), nil
}

// GenerateKey creates a new GPG keypair for the given author identity.
// Stores the private key at ~/.skillpm/gpg/secret.asc and the public
// key at ~/.skillpm/gpg/public.asc
func GenerateKey(name, email string) error {
	secretPath, err := GetSecretKeyPath()
	if err != nil {
		return err
	}

	if _, err := os.Stat(secretPath); err == nil {
		return fmt.Errorf("GPG key already exists at %s. Remove it first to regenerate", secretPath)
	}

	// Create the entity with RSA 4096
	cfg := &packet.Config{
		DefaultHash:            crypto.SHA256,
		DefaultCipher:          packet.CipherAES256,
		DefaultCompressionAlgo: packet.CompressionZLIB,
	}
	entity, err := openpgp.NewEntity(name, "SkillPM Author Key", email, cfg)
	if err != nil {
		return fmt.Errorf("failed to generate key: %w", err)
	}

	// Write private key
	privFile, err := os.OpenFile(secretPath, os.O_CREATE|os.O_WRONLY, 0600)
	if err != nil {
		return fmt.Errorf("failed to create private key file: %w", err)
	}
	defer privFile.Close()

	privWriter, err := armor.Encode(privFile, openpgp.PrivateKeyType, nil)
	if err != nil {
		return err
	}
	if err := entity.SerializePrivate(privWriter, nil); err != nil {
		privWriter.Close()
		return err
	}
	privWriter.Close()

	// Write public key
	pubPath, err := GetPublicKeyPath()
	if err != nil {
		return err
	}

	pubFile, err := os.OpenFile(pubPath, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("failed to create public key file: %w", err)
	}
	defer pubFile.Close()

	pubWriter, err := armor.Encode(pubFile, openpgp.PublicKeyType, nil)
	if err != nil {
		return err
	}
	if err := entity.Serialize(pubWriter); err != nil {
		pubWriter.Close()
		return err
	}
	pubWriter.Close()

	// Print the key fingerprint
	fp := entity.PrimaryKey.Fingerprint
	fpHex := fmt.Sprintf("%X", fp)
	fmt.Printf("Key fingerprint: %s\n", fpHex)
	fmt.Printf("Private key: %s\n", secretPath)
	fmt.Printf("Public key: %s\n", pubPath)

	return nil
}

// ExportPublicKey reads and returns the ASCII-armored public key.
func ExportPublicKey() (string, error) {
	pubPath, err := GetPublicKeyPath()
	if err != nil {
		return "", err
	}

	data, err := os.ReadFile(pubPath)
	if err != nil {
		return "", fmt.Errorf("no public key found. Run 'skillpm auth gen-key' first: %w", err)
	}

	return string(data), nil
}

// Sign creates a detached armored signature for the given data using
// the user's private key.
func Sign(data []byte) ([]byte, error) {
	secretPath, err := GetSecretKeyPath()
	if err != nil {
		return nil, err
	}

	f, err := os.Open(secretPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open private key: %w (run 'skillpm auth gen-key' first)", err)
	}
	defer f.Close()

	entityList, err := openpgp.ReadArmoredKeyRing(f)
	if err != nil {
		return nil, fmt.Errorf("failed to read private key: %w", err)
	}

	if len(entityList) == 0 {
		return nil, fmt.Errorf("no keys found in keyring")
	}

	// Create detached signature
	sigBuf := new(bytes.Buffer)
	err = openpgp.DetachSign(sigBuf, entityList[0], bytes.NewReader(data), nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create signature: %w", err)
	}

	// Armor the raw signature
	armoredBuf := new(bytes.Buffer)
	w, err := armor.Encode(armoredBuf, "PGP SIGNATURE", nil)
	if err != nil {
		return nil, err
	}
	w.Write(sigBuf.Bytes())
	w.Close()

	return armoredBuf.Bytes(), nil
}

// Verify checks a detached signature against the given data and public key.
// publicKeyArmored is the ASCII-armored public key of the skill author.
// signatureArmored is the ASCII-armored detached signature.
func Verify(data []byte, signatureArmored []byte, publicKeyArmored string) error {
	if publicKeyArmored == "" {
		return fmt.Errorf("no public key provided for verification")
	}

	// Parse the public key
	keyRing, err := openpgp.ReadArmoredKeyRing(strings.NewReader(publicKeyArmored))
	if err != nil {
		return fmt.Errorf("failed to parse public key: %w", err)
	}

	if len(keyRing) == 0 {
		return fmt.Errorf("no keys found in public key data")
	}

	// Decode the armored signature
	block, err := armor.Decode(bytes.NewReader(signatureArmored))
	if err != nil {
		return fmt.Errorf("failed to decode signature armor: %w", err)
	}

	// Read the raw signature bytes
	sigBytes, err := io.ReadAll(block.Body)
	if err != nil {
		return fmt.Errorf("failed to read signature body: %w", err)
	}

	// Parse the signature packet
	sigPacket, err := packet.Read(bytes.NewReader(sigBytes))
	if err != nil {
		return fmt.Errorf("failed to parse signature packet: %w", err)
	}

	sig, ok := sigPacket.(*packet.Signature)
	if !ok {
		return fmt.Errorf("not a valid signature packet")
	}

	// Hash the data
	hash := sig.Hash.New()
	hash.Write(data)

	// Verify
	err = keyRing[0].PrimaryKey.VerifySignature(hash, sig)
	if err != nil {
		return fmt.Errorf("signature verification failed: %w", err)
	}

	return nil
}

// VerifyWithLocalKey verifies a signature using the user's own public key.
// Useful for verifying your own packages.
func VerifyWithLocalKey(data, signatureArmored []byte) error {
	pubKey, err := ExportPublicKey()
	if err != nil {
		return err
	}
	return Verify(data, signatureArmored, pubKey)
}

// GetFingerprint returns the fingerprint of the user's public key.
func GetFingerprint() (string, error) {
	pubPath, err := GetPublicKeyPath()
	if err != nil {
		return "", err
	}

	f, err := os.Open(pubPath)
	if err != nil {
		return "", fmt.Errorf("no public key found: %w", err)
	}
	defer f.Close()

	entityList, err := openpgp.ReadArmoredKeyRing(f)
	if err != nil {
		return "", err
	}

	if len(entityList) == 0 {
		return "", fmt.Errorf("no keys found")
	}

	fp := entityList[0].PrimaryKey.Fingerprint
	return fmt.Sprintf("%X", fp), nil
}
