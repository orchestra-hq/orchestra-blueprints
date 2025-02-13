import time
import numpy as np

def power_iteration(A, num_simulations=2500):
    # Starting with a random vector
    b_k = np.random.rand(A.shape[1])
    for _ in range(num_simulations):
        # Multiply by the matrix
        b_k1 = np.dot(A, b_k)
        # Re-normalize the vector
        b_k = b_k1 / np.linalg.norm(b_k1)
    # Estimate the eigenvalue from the result
    eigenvalue = np.dot(b_k.T, np.dot(A, b_k))
    return eigenvalue

def intensive_power_iteration():
    print("Starting power iteration computation...")
    start_time = time.time()
    # Generate a large random matrix
    matrix_size = 20000
    A = np.random.rand(matrix_size, matrix_size)
    # Compute the largest eigenvalue using power iteration
    largest_eigenvalue = power_iteration(A)
    end_time = time.time()
    print("Power iteration computation complete.")
    print(f"Elapsed time: {end_time - start_time:.2f} seconds")
    print(f"Largest estimated eigenvalue: {largest_eigenvalue:.4f}")

intensive_power_iteration()
