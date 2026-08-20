#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p bin
swiftc -O -o bin/bookgrab-helper src/main.swift
echo "✓ bin/bookgrab-helper"
