import math

def display_sf(val: float, ndigits: int, /) -> str:
    if ndigits <= 0:
        raise ValueError("need positive integer number of significant figures")

    if val == 0:
        return f"{0:.{ndigits-1}f}"

    # Preliminary rounding to handle cases like 9.99 -> 10.0
    # This prevents the "magnitude shift" error where it displays an incorrect
    # number of digits
    pre_mag = math.floor(math.log10(abs(val)))
    val = round(val, ndigits - 1 - pre_mag)

    # Recalculate magnitude and decimals based on the rounded value
    magnitude = math.floor(math.log10(abs(val)))
    decimals = ndigits - 1 - magnitude

    if decimals >= 0:
        return f"{val:.{decimals}f}"
    else:
        # Returns as an integer string (e.g., "1200")
        return f"{int(round(val, decimals))}"

def _main():
    # Test cases: (input_val, sig_figs, expected_output)
    test_cases = [
        (1.2345, 3, "1.23"),      # Standard rounding
        (1.2, 4, "1.200"),        # Trailing zeros (your specific requirement)
        (0.0001234, 2, "0.00012"),# Small decimals
        (12345.0, 2, "12000"),    # Large numbers (no decimal)
        (0.0, 3, "0.00"),         # Zero handling
        (-0.005678, 2, "-0.0057"),# Negative small numbers
        (9.99, 2, "10"),          # Rounding up to next magnitude
        (1.001, 2, "1.0"),
        (1.001, 1, "1")
    ]

    print(f"{'Input':>10} | {'SF':>2} | {'Result':>12}")
    print("-" * 30)

    for val, sf, expected in test_cases:
        result = display_sf(val, sf)
        status = "✓" if result == expected else f"✗ (Expected {expected})"
        print(f"{val:10g} | {sf:2} | {result:>12}  {status}")

if __name__ == "__main__":
    _main()