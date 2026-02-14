import { useState, useEffect } from 'react'

// Types
interface Category {
  id: number
  name: string
  description: string | null
  tax_rate: number
}

interface Product {
  id: number
  name: string
  brand: string | null
  category_id: number
  category_name: string | null
  price: number
  case_price: number | null
  case_size: number
  stock_quantity: number
  low_stock_threshold: number
  size: string | null
  abv: number | null
  requires_age_verification: boolean
  is_low_stock: boolean
  times_sold: number
}

interface CartItem {
  product: Product
  quantity: number
}

interface Sale {
  id: number
  subtotal: number
  tax_amount: number
  total: number
  age_verified: boolean
  items: any[]
  created_at: string
}

const API_BASE = '/api'

function App() {
  // State
  const [categories, setCategories] = useState<Category[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [cart, setCart] = useState<CartItem[]>([])
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showAgeModal, setShowAgeModal] = useState(false)
  const [showCheckoutModal, setShowCheckoutModal] = useState(false)
  const [ageVerified, setAgeVerified] = useState(false)
  const [recentSale, setRecentSale] = useState<Sale | null>(null)
  const [lowStockAlert, setLowStockAlert] = useState<Product[]>([])
  const [popularProducts, setPopularProducts] = useState<Product[]>([])
  const [view, setView] = useState<'pos' | 'inventory'>('pos')
  const [showFeedbackModal, setShowFeedbackModal] = useState(false)
  const [feedbackType, setFeedbackType] = useState<'bug' | 'feature'>('bug')
  const [feedbackMessage, setFeedbackMessage] = useState('')
  const [feedbackEmail, setFeedbackEmail] = useState('')
  const [submittingFeedback, setSubmittingFeedback] = useState(false)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)

  // Fetch data on mount
  useEffect(() => {
    fetchCategories()
    fetchProducts()
    fetchLowStock()
    fetchPopularProducts()
  }, [])

  // Fetch functions
  const fetchCategories = async () => {
    try {
      const res = await fetch(`${API_BASE}/categories`)
      const data = await res.json()
      setCategories(data)
    } catch (err) {
      console.error('Failed to fetch categories:', err)
    }
  }

  const fetchProducts = async (categoryId?: number) => {
    try {
      let url = `${API_BASE}/products`
      if (categoryId) {
        url += `?category_id=${categoryId}`
      }
      const res = await fetch(url)
      const data = await res.json()
      setProducts(data)
    } catch (err) {
      console.error('Failed to fetch products:', err)
    }
  }

  const fetchLowStock = async () => {
    try {
      const res = await fetch(`${API_BASE}/inventory/low-stock`)
      const data = await res.json()
      setLowStockAlert(data.products || [])
    } catch (err) {
      console.error('Failed to fetch low stock:', err)
    }
  }

  const fetchPopularProducts = async () => {
    try {
      const res = await fetch(`${API_BASE}/products/popular?limit=5`)
      const data = await res.json()
      setPopularProducts(data)
    } catch (err) {
      console.error('Failed to fetch popular products:', err)
    }
  }

  const searchProducts = async (query: string) => {
    if (!query.trim()) {
      fetchProducts(selectedCategory || undefined)
      return
    }
    try {
      const res = await fetch(`${API_BASE}/products/search?q=${encodeURIComponent(query)}`)
      const data = await res.json()
      setProducts(data)
    } catch (err) {
      console.error('Failed to search products:', err)
    }
  }

  // Cart functions
  const addToCart = (product: Product) => {
    if (product.stock_quantity === 0) return
    
    // Check if alcohol requires age verification
    if (product.requires_age_verification && !ageVerified) {
      setShowAgeModal(true)
      return
    }

    setCart(prev => {
      const existing = prev.find(item => item.product.id === product.id)
      if (existing) {
        if (existing.quantity >= product.stock_quantity) return prev
        return prev.map(item =>
          item.product.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      }
      return [...prev, { product, quantity: 1 }]
    })
  }

  const removeFromCart = (productId: number) => {
    setCart(prev => prev.filter(item => item.product.id !== productId))
  }

  const updateQuantity = (productId: number, quantity: number) => {
    if (quantity <= 0) {
      removeFromCart(productId)
      return
    }
    setCart(prev =>
      prev.map(item =>
        item.product.id === productId
          ? { ...item, quantity: Math.min(quantity, item.product.stock_quantity) }
          : item
      )
    )
  }

  const calculateSubtotal = () => {
    return cart.reduce((sum, item) => {
      // Check for case pricing
      if (item.product.case_price && item.quantity >= item.product.case_size) {
        const cases = Math.floor(item.quantity / item.product.case_size)
        const remaining = item.quantity % item.product.case_size
        return sum + (cases * item.product.case_price) + (remaining * item.product.price)
      }
      return sum + item.product.price * item.quantity
    }, 0)
  }

  const calculateTax = () => {
    // Base tax + category-specific alcohol tax
    return calculateSubtotal() * 0.0875 + cart.reduce((sum, item) => {
      const category = categories.find(c => c.id === item.product.category_id)
      const taxRate = category?.tax_rate || 0
      return sum + (item.product.price * item.quantity * taxRate)
    }, 0)
  }

  const calculateTotal = () => calculateSubtotal() + calculateTax()

  // Checkout
  const handleCheckout = async (paymentMethod: string) => {
    const requiresAge = cart.some(item => item.product.requires_age_verification)
    
    try {
      const res = await fetch(`${API_BASE}/sales`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: cart.map(item => ({
            product_id: item.product.id,
            quantity: item.quantity
          })),
          payment_method: paymentMethod,
          age_verified: requiresAge ? ageVerified : true
        })
      })

      if (!res.ok) {
        const error = await res.json()
        alert(error.detail || 'Checkout failed')
        return
      }

      const sale = await res.json()
      setRecentSale(sale)
      setCart([])
      setShowCheckoutModal(false)
      fetchProducts(selectedCategory || undefined)
      fetchLowStock()
      fetchPopularProducts()
    } catch (err) {
      console.error('Checkout failed:', err)
      alert('Checkout failed')
    }
  }

  const confirmAge = () => {
    setAgeVerified(true)
    setShowAgeModal(false)
  }

  // Feedback submission
  const submitFeedback = async () => {
    if (!feedbackMessage.trim()) return
    setSubmittingFeedback(true)
    try {
      await fetch(`${API_BASE}/feedback/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: feedbackType,
          message: feedbackMessage.trim(),
          email: feedbackEmail.trim() || null,
          page_url: window.location.href,
          user_agent: navigator.userAgent
        })
      })
      setFeedbackSubmitted(true)
      setTimeout(() => {
        setShowFeedbackModal(false)
        setFeedbackSubmitted(false)
        setFeedbackMessage('')
        setFeedbackEmail('')
      }, 2000)
    } catch (e) {
      console.error('Feedback submission failed:', e)
    }
    setSubmittingFeedback(false)
  }

  // Category filter
  const handleCategoryChange = (categoryId: number | null) => {
    setSelectedCategory(categoryId)
    setSearchQuery('')
    if (categoryId) {
      fetchProducts(categoryId)
    } else {
      fetchProducts()
    }
  }

  // Search debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      searchProducts(searchQuery)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-purple-700 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold">🍷 Liquor Store POS</h1>
            {ageVerified && (
              <span className="bg-green-500 text-white text-xs px-2 py-1 rounded-full">
                21+ Verified
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setView('pos')}
              className={`btn ${view === 'pos' ? 'bg-white text-purple-700' : 'bg-purple-600 text-white'}`}
            >
              POS
            </button>
            <button
              onClick={() => setView('inventory')}
              className={`btn ${view === 'inventory' ? 'bg-white text-purple-700' : 'bg-purple-600 text-white'}`}
            >
              Inventory
              {lowStockAlert.length > 0 && (
                <span className="ml-2 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                  {lowStockAlert.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {view === 'pos' ? (
        <div className="max-w-7xl mx-auto px-4 py-6 flex gap-6">
          {/* Products Section */}
          <div className="flex-1">
            {/* Search */}
            <div className="mb-4">
              <input
                type="text"
                placeholder="Search products by name, brand, or barcode..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input text-lg"
              />
            </div>

            {/* Categories */}
            <div className="flex gap-2 mb-4 flex-wrap">
              <button
                onClick={() => handleCategoryChange(null)}
                className={`category-tab ${!selectedCategory ? 'active' : ''}`}
              >
                All
              </button>
              {categories.map(cat => (
                <button
                  key={cat.id}
                  onClick={() => handleCategoryChange(cat.id)}
                  className={`category-tab ${selectedCategory === cat.id ? 'active' : ''}`}
                >
                  {cat.name}
                </button>
              ))}
            </div>

            {/* Popular Products */}
            {!searchQuery && !selectedCategory && popularProducts.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-700 mb-3">🔥 Popular Items</h3>
                <div className="flex gap-3 overflow-x-auto pb-2">
                  {popularProducts.map(product => (
                    <button
                      key={product.id}
                      onClick={() => addToCart(product)}
                      className="flex-shrink-0 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg px-4 py-2 hover:from-purple-600 hover:to-purple-700 transition-all"
                    >
                      {product.name} - ${product.price.toFixed(2)}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Product Grid */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {products.map(product => (
                <div
                  key={product.id}
                  onClick={() => addToCart(product)}
                  className={`product-card ${product.is_low_stock && product.stock_quantity > 0 ? 'low-stock' : ''} ${product.stock_quantity === 0 ? 'out-of-stock' : ''}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs text-gray-500">{product.category_name}</span>
                    {product.requires_age_verification && (
                      <span className="text-xs bg-red-100 text-red-600 px-1 rounded">21+</span>
                    )}
                  </div>
                  <h3 className="font-semibold text-gray-900">{product.name}</h3>
                  {product.brand && (
                    <p className="text-sm text-gray-600">{product.brand}</p>
                  )}
                  {product.size && (
                    <p className="text-xs text-gray-500">{product.size}</p>
                  )}
                  <div className="mt-2 flex justify-between items-end">
                    <div>
                      <span className="text-lg font-bold text-purple-600">
                        ${product.price.toFixed(2)}
                      </span>
                      {product.case_price && (
                        <span className="text-xs text-gray-500 block">
                          Case ({product.case_size}): ${product.case_price.toFixed(2)}
                        </span>
                      )}
                    </div>
                    <span className={`text-xs ${product.stock_quantity === 0 ? 'text-red-600' : product.is_low_stock ? 'text-yellow-600' : 'text-gray-500'}`}>
                      {product.stock_quantity === 0 ? 'Out of Stock' : `${product.stock_quantity} left`}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cart Section */}
          <div className="w-96 bg-white rounded-xl shadow-lg p-6 h-fit sticky top-6">
            <h2 className="text-xl font-bold mb-4">🛒 Cart</h2>
            
            {cart.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Cart is empty</p>
            ) : (
              <>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {cart.map(item => (
                    <div key={item.product.id} className="cart-item">
                      <div className="flex-1">
                        <p className="font-medium">{item.product.name}</p>
                        <p className="text-sm text-gray-500">
                          ${item.product.price.toFixed(2)} each
                          {item.product.case_price && item.quantity >= item.product.case_size && (
                            <span className="text-green-600 ml-1">
                              (Case pricing!)
                            </span>
                          )}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => updateQuantity(item.product.id, item.quantity - 1)}
                          className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center"
                        >
                          -
                        </button>
                        <span className="w-8 text-center font-medium">{item.quantity}</span>
                        <button
                          onClick={() => updateQuantity(item.product.id, item.quantity + 1)}
                          className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center"
                        >
                          +
                        </button>
                        <button
                          onClick={() => removeFromCart(item.product.id)}
                          className="ml-2 text-red-500 hover:text-red-700"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="border-t mt-4 pt-4 space-y-2">
                  <div className="flex justify-between text-gray-600">
                    <span>Subtotal</span>
                    <span>${calculateSubtotal().toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-gray-600">
                    <span>Tax</span>
                    <span>${calculateTax().toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-xl font-bold">
                    <span>Total</span>
                    <span>${calculateTotal().toFixed(2)}</span>
                  </div>
                </div>

                <button
                  onClick={() => setShowCheckoutModal(true)}
                  className="w-full btn btn-success mt-4 text-lg py-3"
                >
                  Checkout
                </button>
              </>
            )}
          </div>
        </div>
      ) : (
        /* Inventory View */
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Low Stock Alerts */}
            <div className="card">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                ⚠️ Low Stock Alerts
                <span className="bg-red-500 text-white text-sm px-2 py-0.5 rounded-full">
                  {lowStockAlert.length}
                </span>
              </h2>
              {lowStockAlert.length === 0 ? (
                <p className="text-gray-500">All products are well stocked!</p>
              ) : (
                <div className="space-y-3">
                  {lowStockAlert.map((product: any) => (
                    <div key={product.id} className={`p-3 rounded-lg ${product.needs_reorder ? 'bg-red-50 border border-red-200' : 'bg-yellow-50 border border-yellow-200'}`}>
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="font-medium">{product.name}</p>
                          <p className="text-sm text-gray-600">{product.brand} • {product.category}</p>
                        </div>
                        <div className="text-right">
                          <span className={`text-lg font-bold ${product.needs_reorder ? 'text-red-600' : 'text-yellow-600'}`}>
                            {product.stock_quantity}
                          </span>
                          <p className="text-xs text-gray-500">units left</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Inventory Summary */}
            <div className="card">
              <h2 className="text-xl font-bold mb-4">📊 Inventory Summary</h2>
              <div className="space-y-4">
                {categories.map(cat => {
                  const catProducts = products.filter(p => p.category_id === cat.id)
                  const totalStock = catProducts.reduce((sum, p) => sum + p.stock_quantity, 0)
                  const totalValue = catProducts.reduce((sum, p) => sum + (p.price * p.stock_quantity), 0)
                  
                  return (
                    <div key={cat.id} className="p-3 bg-gray-50 rounded-lg">
                      <div className="flex justify-between items-center">
                        <span className="font-medium">{cat.name}</span>
                        <span className="text-gray-600">{catProducts.length} products</span>
                      </div>
                      <div className="flex justify-between text-sm text-gray-500 mt-1">
                        <span>{totalStock} units</span>
                        <span>${totalValue.toFixed(2)} value</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Age Verification Modal */}
      {showAgeModal && (
        <div className="modal-backdrop" onClick={() => setShowAgeModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="text-center">
              <div className="text-6xl mb-4">🍺</div>
              <h2 className="text-2xl font-bold mb-2">Age Verification Required</h2>
              <p className="text-gray-600 mb-6">
                This product contains alcohol. Please verify that the customer is 21 years of age or older.
              </p>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={() => setShowAgeModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmAge}
                  className="btn btn-primary"
                >
                  ✓ Customer is 21+
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Checkout Modal */}
      {showCheckoutModal && (
        <div className="modal-backdrop" onClick={() => setShowCheckoutModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">Select Payment Method</h2>
            <div className="text-center mb-6">
              <span className="text-3xl font-bold text-purple-600">
                ${calculateTotal().toFixed(2)}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => handleCheckout('cash')}
                className="btn bg-green-500 text-white hover:bg-green-600 py-4 text-lg"
              >
                💵 Cash
              </button>
              <button
                onClick={() => handleCheckout('card')}
                className="btn bg-blue-500 text-white hover:bg-blue-600 py-4 text-lg"
              >
                💳 Card
              </button>
            </div>
            <button
              onClick={() => setShowCheckoutModal(false)}
              className="w-full btn btn-secondary mt-4"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Sale Complete Toast */}
      {recentSale && (
        <div className="fixed bottom-6 right-24 bg-green-600 text-white rounded-xl shadow-2xl p-6 max-w-sm animate-pulse">
          <div className="flex items-center gap-3">
            <span className="text-3xl">✓</span>
            <div>
              <p className="font-bold">Sale Complete!</p>
              <p className="text-sm opacity-90">
                Sale #{recentSale.id} • ${recentSale.total.toFixed(2)}
              </p>
            </div>
          </div>
          <button
            onClick={() => setRecentSale(null)}
            className="absolute top-2 right-2 text-white opacity-70 hover:opacity-100"
          >
            ✕
          </button>
        </div>
      )}

      {/* Floating Feedback Button */}
      <button
        onClick={() => setShowFeedbackModal(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-purple-600 text-white rounded-full shadow-lg hover:bg-purple-700 hover:scale-110 transition-all flex items-center justify-center text-2xl z-50"
        title="Send Feedback"
      >
        💬
      </button>

      {/* Feedback Modal */}
      {showFeedbackModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]">
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-lg w-full mx-4">
            {feedbackSubmitted ? (
              <div className="text-center py-8">
                <div className="text-5xl mb-4">✅</div>
                <h2 className="text-2xl font-bold text-green-600">Thank you!</h2>
                <p className="text-gray-500 mt-2">Your feedback has been submitted.</p>
              </div>
            ) : (
              <>
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-bold">Send Feedback</h2>
                  <button onClick={() => setShowFeedbackModal(false)} className="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
                </div>
                
                <div className="flex gap-2 mb-4">
                  <button
                    onClick={() => setFeedbackType('bug')}
                    className={`flex-1 py-3 rounded-lg font-semibold transition ${
                      feedbackType === 'bug' ? 'bg-red-600 text-white' : 'bg-gray-100 hover:bg-gray-200'
                    }`}
                  >
                    🐛 Bug Report
                  </button>
                  <button
                    onClick={() => setFeedbackType('feature')}
                    className={`flex-1 py-3 rounded-lg font-semibold transition ${
                      feedbackType === 'feature' ? 'bg-purple-600 text-white' : 'bg-gray-100 hover:bg-gray-200'
                    }`}
                  >
                    💡 Feature Request
                  </button>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1">
                      {feedbackType === 'bug' ? 'What went wrong?' : 'What would you like?'}
                    </label>
                    <textarea
                      placeholder={feedbackType === 'bug' 
                        ? 'Describe the issue and steps to reproduce...'
                        : 'Describe the feature and how it would help...'}
                      value={feedbackMessage}
                      onChange={e => setFeedbackMessage(e.target.value)}
                      rows={4}
                      className="w-full p-3 border-2 rounded-lg focus:border-purple-500 focus:outline-none resize-none"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1">Email (optional)</label>
                    <input
                      type="email"
                      placeholder="your@email.com"
                      value={feedbackEmail}
                      onChange={e => setFeedbackEmail(e.target.value)}
                      className="w-full p-3 border-2 rounded-lg focus:border-purple-500 focus:outline-none"
                    />
                  </div>
                </div>
                
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => setShowFeedbackModal(false)}
                    className="flex-1 py-3 bg-gray-200 rounded-lg font-semibold hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={submitFeedback}
                    disabled={submittingFeedback || !feedbackMessage.trim()}
                    className="flex-1 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-300"
                  >
                    {submittingFeedback ? 'Sending...' : 'Submit'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default App
