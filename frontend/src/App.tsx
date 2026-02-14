import { useState, useEffect, useCallback } from 'react'

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

interface Customer {
  id: number
  name: string
  phone: string
  email: string | null
  loyalty_points: number
  total_spent: number
  join_date: string
  taste_preferences?: TasteProfile
}

interface TasteProfile {
  preferred_spirits: string[]
  preferred_wines: string[]
  preferred_beer_styles: string[]
  favorite_brands: string[]
  notes: string
}

interface GiftCard {
  id: number
  code: string
  original_balance: number
  current_balance: number
  is_active: boolean
  created_at: string
  expires_at: string | null
}

interface TastingEvent {
  id: number
  name: string
  description: string
  event_date: string
  start_time: string
  end_time: string
  max_attendees: number
  current_attendees: number
  price_per_person: number
  products_featured: number[]
  status: 'scheduled' | 'cancelled' | 'completed'
}

interface DeliveryOrder {
  id: number
  sale_id: number
  customer_name: string
  address: string
  phone: string
  status: 'pending' | 'assigned' | 'out_for_delivery' | 'delivered' | 'cancelled'
  driver_name: string | null
  scheduled_time: string
  delivery_notes: string
  created_at: string
}

interface Shift {
  id: number
  employee_name: string
  start_time: string
  end_time: string | null
  status: 'active' | 'completed'
  total_sales: number
  transactions: number
}

interface CashDrawer {
  id: number
  opening_amount: number
  current_amount: number
  expected_amount: number
  status: 'open' | 'closed'
  opened_at: string
  closed_at: string | null
}

interface HappyHour {
  id: number
  name: string
  day_of_week: number
  start_time: string
  end_time: string
  discount_percent: number
  categories: number[]
  is_active: boolean
}

interface Report {
  total_sales: number
  total_transactions: number
  average_transaction: number
  top_products: { name: string; quantity: number; revenue: number }[]
  sales_by_category: { category: string; revenue: number }[]
  sales_by_hour: { hour: number; revenue: number }[]
}

type ViewMode = 'pos' | 'inventory' | 'dashboard' | 'customers' | 'reports' | 'delivery' | 'events' | 'settings'

const API_BASE = '/api'

// Utility functions
const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`
const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString()
const formatTime = (timeStr: string) => {
  const [hours, minutes] = timeStr.split(':')
  const h = parseInt(hours)
  return `${h > 12 ? h - 12 : h}:${minutes} ${h >= 12 ? 'PM' : 'AM'}`
}
const formatDateTime = (dateStr: string) => new Date(dateStr).toLocaleString()

function App() {
  // Core state
  const [view, setView] = useState<ViewMode>('pos')
  const [categories, setCategories] = useState<Category[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [cart, setCart] = useState<CartItem[]>([])
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [ageVerified, setAgeVerified] = useState(false)
  const [recentSale, setRecentSale] = useState<Sale | null>(null)
  const [lowStockAlert, setLowStockAlert] = useState<Product[]>([])
  const [popularProducts, setPopularProducts] = useState<Product[]>([])

  // Modal states
  const [showAgeModal, setShowAgeModal] = useState(false)
  const [showCheckoutModal, setShowCheckoutModal] = useState(false)
  const [showFeedbackModal, setShowFeedbackModal] = useState(false)
  const [showGiftCardModal, setShowGiftCardModal] = useState(false)
  const [showNewCustomerModal, setShowNewCustomerModal] = useState(false)
  const [showEventModal, setShowEventModal] = useState(false)
  const [showCashDrawerModal, setShowCashDrawerModal] = useState(false)
  const [showShiftModal, setShowShiftModal] = useState(false)
  const [showReturnModal, setShowReturnModal] = useState(false)

  // Feedback state
  const [feedbackType, setFeedbackType] = useState<'bug' | 'feature'>('bug')
  const [feedbackMessage, setFeedbackMessage] = useState('')
  const [feedbackEmail, setFeedbackEmail] = useState('')
  const [submittingFeedback, setSubmittingFeedback] = useState(false)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)

  // Dashboard state
  const [dashboardStats, setDashboardStats] = useState({
    todaySales: 0,
    todayTransactions: 0,
    averageTransaction: 0,
    activeHappyHour: null as HappyHour | null,
    lowStockCount: 0,
    pendingDeliveries: 0,
    upcomingEvents: 0
  })

  // Customer state
  const [customers, setCustomers] = useState<Customer[]>([])
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [customerSearch, setCustomerSearch] = useState('')
  const [newCustomer, setNewCustomer] = useState({ name: '', phone: '', email: '' })
  const [customerTab, setCustomerTab] = useState<'list' | 'loyalty' | 'taste'>('list')

  // Reports state
  const [reportPeriod, setReportPeriod] = useState<'today' | 'week' | 'month'>('today')
  const [reportData, setReportData] = useState<Report | null>(null)
  const [loadingReport, setLoadingReport] = useState(false)

  // Delivery state
  const [deliveryOrders, setDeliveryOrders] = useState<DeliveryOrder[]>([])
  const [deliveryFilter, setDeliveryFilter] = useState<string>('all')

  // Events state
  const [tastingEvents, setTastingEvents] = useState<TastingEvent[]>([])
  const [newEvent, setNewEvent] = useState({
    name: '', description: '', event_date: '', start_time: '', end_time: '',
    max_attendees: 20, price_per_person: 25
  })

  // Settings state
  const [settingsTab, setSettingsTab] = useState<'store' | 'employees' | 'happyhour' | 'seasonal'>('store')
  const [storeSettings, setStoreSettings] = useState({
    name: 'Craft & Cork Liquor',
    address: '',
    phone: '',
    opening_time: '10:00',
    closing_time: '22:00'
  })
  const [happyHours, setHappyHours] = useState<HappyHour[]>([])
  const [employees, setEmployees] = useState<any[]>([])

  // Gift card state
  const [giftCardCode, setGiftCardCode] = useState('')
  const [giftCardAmount, setGiftCardAmount] = useState(25)
  const [appliedGiftCard, setAppliedGiftCard] = useState<GiftCard | null>(null)

  // Shift & Cash Drawer state
  const [currentShift, setCurrentShift] = useState<Shift | null>(null)
  const [cashDrawer, setCashDrawer] = useState<CashDrawer | null>(null)
  const [drawerAmount, setDrawerAmount] = useState(200)

  // Return state
  const [returnSaleId, setReturnSaleId] = useState('')
  const [returnReason, setReturnReason] = useState('')

  // Toast state
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null)

  // Show toast helper
  const showToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }, [])

  // Fetch data on mount
  useEffect(() => {
    fetchCategories()
    fetchProducts()
    fetchLowStock()
    fetchPopularProducts()
    fetchDashboardStats()
    fetchCurrentShift()
    fetchCashDrawer()
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
      if (categoryId) url += `?category_id=${categoryId}`
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

  const fetchDashboardStats = async () => {
    try {
      const [salesRes, happyRes, deliveryRes, eventsRes] = await Promise.all([
        fetch(`${API_BASE}/dashboard/today`).catch(() => null),
        fetch(`${API_BASE}/happy-hour/active`).catch(() => null),
        fetch(`${API_BASE}/delivery/pending`).catch(() => null),
        fetch(`${API_BASE}/tasting-events/upcoming`).catch(() => null)
      ])
      
      const sales = salesRes?.ok ? await salesRes.json() : { total: 0, count: 0 }
      const happy = happyRes?.ok ? await happyRes.json() : null
      const deliveries = deliveryRes?.ok ? await deliveryRes.json() : []
      const events = eventsRes?.ok ? await eventsRes.json() : []
      
      setDashboardStats({
        todaySales: sales.total || 0,
        todayTransactions: sales.count || 0,
        averageTransaction: sales.count > 0 ? sales.total / sales.count : 0,
        activeHappyHour: happy,
        lowStockCount: lowStockAlert.length,
        pendingDeliveries: Array.isArray(deliveries) ? deliveries.length : 0,
        upcomingEvents: Array.isArray(events) ? events.length : 0
      })
    } catch (err) {
      console.error('Failed to fetch dashboard stats:', err)
    }
  }

  const fetchCustomers = async (search?: string) => {
    try {
      let url = `${API_BASE}/customers`
      if (search) url += `?search=${encodeURIComponent(search)}`
      const res = await fetch(url)
      const data = await res.json()
      setCustomers(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch customers:', err)
    }
  }

  const fetchReports = async (period: string) => {
    setLoadingReport(true)
    try {
      const res = await fetch(`${API_BASE}/reports/${period}`)
      if (res.ok) {
        const data = await res.json()
        setReportData(data)
      }
    } catch (err) {
      console.error('Failed to fetch reports:', err)
    }
    setLoadingReport(false)
  }

  const fetchDeliveryOrders = async () => {
    try {
      const res = await fetch(`${API_BASE}/delivery/orders`)
      const data = await res.json()
      setDeliveryOrders(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch delivery orders:', err)
    }
  }

  const fetchTastingEvents = async () => {
    try {
      const res = await fetch(`${API_BASE}/tasting-events`)
      const data = await res.json()
      setTastingEvents(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch tasting events:', err)
    }
  }

  const fetchHappyHours = async () => {
    try {
      const res = await fetch(`${API_BASE}/happy-hour`)
      const data = await res.json()
      setHappyHours(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch happy hours:', err)
    }
  }

  const fetchEmployees = async () => {
    try {
      const res = await fetch(`${API_BASE}/employees`)
      const data = await res.json()
      setEmployees(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch employees:', err)
    }
  }

  const fetchCurrentShift = async () => {
    try {
      const res = await fetch(`${API_BASE}/shifts/current`)
      if (res.ok) {
        const data = await res.json()
        setCurrentShift(data)
      }
    } catch (err) {
      console.error('Failed to fetch current shift:', err)
    }
  }

  const fetchCashDrawer = async () => {
    try {
      const res = await fetch(`${API_BASE}/cash-drawer/current`)
      if (res.ok) {
        const data = await res.json()
        setCashDrawer(data)
      }
    } catch (err) {
      console.error('Failed to fetch cash drawer:', err)
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

  // View change effect
  useEffect(() => {
    if (view === 'customers') fetchCustomers()
    if (view === 'reports') fetchReports(reportPeriod)
    if (view === 'delivery') fetchDeliveryOrders()
    if (view === 'events') fetchTastingEvents()
    if (view === 'settings') {
      fetchHappyHours()
      fetchEmployees()
    }
  }, [view, reportPeriod])

  // Cart functions
  const addToCart = (product: Product) => {
    if (product.stock_quantity === 0) {
      showToast('Product is out of stock', 'error')
      return
    }
    
    if (product.requires_age_verification && !ageVerified) {
      setShowAgeModal(true)
      return
    }

    setCart(prev => {
      const existing = prev.find(item => item.product.id === product.id)
      if (existing) {
        if (existing.quantity >= product.stock_quantity) {
          showToast('Maximum stock reached', 'error')
          return prev
        }
        return prev.map(item =>
          item.product.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      }
      return [...prev, { product, quantity: 1 }]
    })
    showToast(`Added ${product.name}`, 'success')
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
      if (item.product.case_price && item.quantity >= item.product.case_size) {
        const cases = Math.floor(item.quantity / item.product.case_size)
        const remaining = item.quantity % item.product.case_size
        return sum + (cases * item.product.case_price) + (remaining * item.product.price)
      }
      return sum + item.product.price * item.quantity
    }, 0)
  }

  const calculateTax = () => {
    return calculateSubtotal() * 0.0875 + cart.reduce((sum, item) => {
      const category = categories.find(c => c.id === item.product.category_id)
      const taxRate = category?.tax_rate || 0
      return sum + (item.product.price * item.quantity * taxRate)
    }, 0)
  }

  const calculateGiftCardDiscount = () => {
    if (!appliedGiftCard) return 0
    const total = calculateSubtotal() + calculateTax()
    return Math.min(appliedGiftCard.current_balance, total)
  }

  const calculateTotal = () => calculateSubtotal() + calculateTax() - calculateGiftCardDiscount()

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
          age_verified: requiresAge ? ageVerified : true,
          customer_id: selectedCustomer?.id,
          gift_card_code: appliedGiftCard?.code
        })
      })

      if (!res.ok) {
        const error = await res.json()
        showToast(error.detail || 'Checkout failed', 'error')
        return
      }

      const sale = await res.json()
      setRecentSale(sale)
      setCart([])
      setAppliedGiftCard(null)
      setShowCheckoutModal(false)
      fetchProducts(selectedCategory || undefined)
      fetchLowStock()
      fetchPopularProducts()
      fetchDashboardStats()
      showToast(`Sale #${sale.id} completed!`, 'success')
    } catch (err) {
      console.error('Checkout failed:', err)
      showToast('Checkout failed', 'error')
    }
  }

  const confirmAge = () => {
    setAgeVerified(true)
    setShowAgeModal(false)
    showToast('Age verified - 21+', 'success')
  }

  // Customer functions
  const createCustomer = async () => {
    try {
      const res = await fetch(`${API_BASE}/customers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCustomer)
      })
      if (res.ok) {
        const customer = await res.json()
        setCustomers(prev => [customer, ...prev])
        setShowNewCustomerModal(false)
        setNewCustomer({ name: '', phone: '', email: '' })
        showToast('Customer created!', 'success')
      }
    } catch (err) {
      showToast('Failed to create customer', 'error')
    }
  }

  // Gift card functions
  const applyGiftCard = async () => {
    try {
      const res = await fetch(`${API_BASE}/gift-cards/${giftCardCode}`)
      if (res.ok) {
        const card = await res.json()
        if (card.is_active && card.current_balance > 0) {
          setAppliedGiftCard(card)
          setShowGiftCardModal(false)
          showToast(`Gift card applied: ${formatCurrency(card.current_balance)} balance`, 'success')
        } else {
          showToast('Gift card is invalid or has no balance', 'error')
        }
      } else {
        showToast('Gift card not found', 'error')
      }
    } catch (err) {
      showToast('Failed to apply gift card', 'error')
    }
  }

  const createGiftCard = async () => {
    try {
      const res = await fetch(`${API_BASE}/gift-cards`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: giftCardAmount })
      })
      if (res.ok) {
        const card = await res.json()
        showToast(`Gift card created: ${card.code}`, 'success')
      }
    } catch (err) {
      showToast('Failed to create gift card', 'error')
    }
  }

  // Shift functions
  const startShift = async () => {
    try {
      const res = await fetch(`${API_BASE}/shifts/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ employee_name: 'Current Employee' })
      })
      if (res.ok) {
        const shift = await res.json()
        setCurrentShift(shift)
        showToast('Shift started!', 'success')
      }
    } catch (err) {
      showToast('Failed to start shift', 'error')
    }
  }

  const endShift = async () => {
    if (!currentShift) return
    try {
      const res = await fetch(`${API_BASE}/shifts/${currentShift.id}/end`, {
        method: 'POST'
      })
      if (res.ok) {
        setCurrentShift(null)
        showToast('Shift ended!', 'success')
      }
    } catch (err) {
      showToast('Failed to end shift', 'error')
    }
  }

  // Cash drawer functions
  const openCashDrawer = async () => {
    try {
      const res = await fetch(`${API_BASE}/cash-drawer/open`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ opening_amount: drawerAmount })
      })
      if (res.ok) {
        const drawer = await res.json()
        setCashDrawer(drawer)
        setShowCashDrawerModal(false)
        showToast('Cash drawer opened!', 'success')
      }
    } catch (err) {
      showToast('Failed to open cash drawer', 'error')
    }
  }

  const closeCashDrawer = async () => {
    if (!cashDrawer) return
    try {
      const res = await fetch(`${API_BASE}/cash-drawer/${cashDrawer.id}/close`, {
        method: 'POST'
      })
      if (res.ok) {
        setCashDrawer(null)
        showToast('Cash drawer closed!', 'success')
      }
    } catch (err) {
      showToast('Failed to close cash drawer', 'error')
    }
  }

  // Event functions
  const createTastingEvent = async () => {
    try {
      const res = await fetch(`${API_BASE}/tasting-events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEvent)
      })
      if (res.ok) {
        fetchTastingEvents()
        setShowEventModal(false)
        setNewEvent({
          name: '', description: '', event_date: '', start_time: '', end_time: '',
          max_attendees: 20, price_per_person: 25
        })
        showToast('Event created!', 'success')
      }
    } catch (err) {
      showToast('Failed to create event', 'error')
    }
  }

  // Delivery functions
  const updateDeliveryStatus = async (orderId: number, status: string) => {
    try {
      const res = await fetch(`${API_BASE}/delivery/orders/${orderId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      })
      if (res.ok) {
        fetchDeliveryOrders()
        showToast('Delivery status updated!', 'success')
      }
    } catch (err) {
      showToast('Failed to update delivery status', 'error')
    }
  }

  // Return functions
  const processReturn = async () => {
    try {
      const res = await fetch(`${API_BASE}/returns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sale_id: parseInt(returnSaleId), reason: returnReason })
      })
      if (res.ok) {
        setShowReturnModal(false)
        setReturnSaleId('')
        setReturnReason('')
        showToast('Return processed!', 'success')
      }
    } catch (err) {
      showToast('Failed to process return', 'error')
    }
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

  // Customer search debounce
  useEffect(() => {
    if (customerSearch) {
      const timer = setTimeout(() => {
        fetchCustomers(customerSearch)
      }, 300)
      return () => clearTimeout(timer)
    }
  }, [customerSearch])

  // Navigation component
  const Navigation = () => (
    <nav className="bg-purple-800 text-white">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex gap-1 py-2 overflow-x-auto">
          {[
            { id: 'pos', label: '🛒 POS', badge: cart.length > 0 ? cart.length : undefined },
            { id: 'dashboard', label: '📊 Dashboard' },
            { id: 'customers', label: '👥 Customers' },
            { id: 'inventory', label: '📦 Inventory', badge: lowStockAlert.length > 0 ? lowStockAlert.length : undefined },
            { id: 'reports', label: '📈 Reports' },
            { id: 'delivery', label: '🚗 Delivery', badge: dashboardStats.pendingDeliveries > 0 ? dashboardStats.pendingDeliveries : undefined },
            { id: 'events', label: '🍷 Events' },
            { id: 'settings', label: '⚙️ Settings' }
          ].map(nav => (
            <button
              key={nav.id}
              onClick={() => setView(nav.id as ViewMode)}
              className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-all ${
                view === nav.id
                  ? 'bg-white text-purple-700'
                  : 'bg-purple-700 text-white hover:bg-purple-600'
              }`}
            >
              {nav.label}
              {nav.badge && (
                <span className="ml-2 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                  {nav.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
    </nav>
  )

  // Dashboard View
  const DashboardView = () => (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card bg-gradient-to-br from-purple-500 to-purple-700 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-200 text-sm">Today's Sales</p>
              <p className="text-3xl font-bold">{formatCurrency(dashboardStats.todaySales)}</p>
            </div>
            <div className="text-5xl opacity-50">💰</div>
          </div>
          <p className="text-purple-200 text-sm mt-2">
            {dashboardStats.todayTransactions} transactions
          </p>
        </div>

        <div className="card bg-gradient-to-br from-green-500 to-green-700 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-200 text-sm">Average Transaction</p>
              <p className="text-3xl font-bold">{formatCurrency(dashboardStats.averageTransaction)}</p>
            </div>
            <div className="text-5xl opacity-50">📊</div>
          </div>
        </div>

        <div className="card bg-gradient-to-br from-blue-500 to-blue-700 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-200 text-sm">Pending Deliveries</p>
              <p className="text-3xl font-bold">{dashboardStats.pendingDeliveries}</p>
            </div>
            <div className="text-5xl opacity-50">🚗</div>
          </div>
        </div>

        <div className="card bg-gradient-to-br from-orange-500 to-orange-700 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-orange-200 text-sm">Low Stock Items</p>
              <p className="text-3xl font-bold">{lowStockAlert.length}</p>
            </div>
            <div className="text-5xl opacity-50">⚠️</div>
          </div>
        </div>
      </div>

      {/* Happy Hour Alert */}
      {dashboardStats.activeHappyHour && (
        <div className="bg-gradient-to-r from-yellow-400 to-orange-500 rounded-xl p-6 text-white shadow-lg">
          <div className="flex items-center gap-4">
            <span className="text-5xl">🎉</span>
            <div>
              <h3 className="text-2xl font-bold">Happy Hour Active!</h3>
              <p className="text-yellow-100">
                {dashboardStats.activeHappyHour.name} - {dashboardStats.activeHappyHour.discount_percent}% off select items
              </p>
              <p className="text-sm text-yellow-200 mt-1">
                Until {formatTime(dashboardStats.activeHappyHour.end_time)}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quick Actions */}
        <div className="card">
          <h3 className="text-xl font-bold mb-4">⚡ Quick Actions</h3>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setShowCashDrawerModal(true)}
              className="btn bg-purple-100 text-purple-700 hover:bg-purple-200 py-4"
            >
              💵 Cash Drawer
            </button>
            <button
              onClick={() => setShowShiftModal(true)}
              className="btn bg-blue-100 text-blue-700 hover:bg-blue-200 py-4"
            >
              ⏱️ Shift Management
            </button>
            <button
              onClick={() => setShowGiftCardModal(true)}
              className="btn bg-green-100 text-green-700 hover:bg-green-200 py-4"
            >
              🎁 Gift Cards
            </button>
            <button
              onClick={() => setShowReturnModal(true)}
              className="btn bg-red-100 text-red-700 hover:bg-red-200 py-4"
            >
              ↩️ Process Return
            </button>
            <button
              onClick={() => setView('events')}
              className="btn bg-yellow-100 text-yellow-700 hover:bg-yellow-200 py-4"
            >
              🍷 Tasting Events
            </button>
            <button
              onClick={() => setView('reports')}
              className="btn bg-indigo-100 text-indigo-700 hover:bg-indigo-200 py-4"
            >
              📈 View Reports
            </button>
          </div>
        </div>

        {/* Current Shift & Drawer Status */}
        <div className="card">
          <h3 className="text-xl font-bold mb-4">📋 Current Status</h3>
          <div className="space-y-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-medium">Shift Status</p>
                  <p className="text-sm text-gray-600">
                    {currentShift ? `Active since ${formatDateTime(currentShift.start_time)}` : 'No active shift'}
                  </p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  currentShift ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                }`}>
                  {currentShift ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-medium">Cash Drawer</p>
                  <p className="text-sm text-gray-600">
                    {cashDrawer ? `${formatCurrency(cashDrawer.current_amount)} in drawer` : 'Drawer closed'}
                  </p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  cashDrawer?.status === 'open' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                }`}>
                  {cashDrawer?.status === 'open' ? 'Open' : 'Closed'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Low Stock Alerts */}
      {lowStockAlert.length > 0 && (
        <div className="card border-l-4 border-red-500">
          <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
            ⚠️ Low Stock Alerts
            <span className="bg-red-500 text-white text-sm px-2 py-0.5 rounded-full">
              {lowStockAlert.length}
            </span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {lowStockAlert.slice(0, 6).map((product: any) => (
              <div key={product.id} className="p-3 bg-red-50 rounded-lg border border-red-200">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-gray-900">{product.name}</p>
                    <p className="text-sm text-gray-600">{product.brand}</p>
                  </div>
                  <span className="text-lg font-bold text-red-600">{product.stock_quantity}</span>
                </div>
              </div>
            ))}
          </div>
          {lowStockAlert.length > 6 && (
            <button
              onClick={() => setView('inventory')}
              className="mt-4 text-purple-600 hover:text-purple-800 font-medium"
            >
              View all {lowStockAlert.length} alerts →
            </button>
          )}
        </div>
      )}

      {/* Popular Products */}
      {popularProducts.length > 0 && (
        <div className="card">
          <h3 className="text-xl font-bold mb-4">🔥 Top Sellers Today</h3>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {popularProducts.map((product, index) => (
              <div key={product.id} className="text-center p-4 bg-purple-50 rounded-lg">
                <span className="text-3xl">{index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '🏅'}</span>
                <p className="font-medium mt-2">{product.name}</p>
                <p className="text-sm text-gray-600">{product.times_sold} sold</p>
                <p className="text-purple-600 font-bold">{formatCurrency(product.price)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  // Customers View
  const CustomersView = () => (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Customer Tabs */}
      <div className="flex gap-2 mb-6">
        {[
          { id: 'list', label: '👥 All Customers' },
          { id: 'loyalty', label: '⭐ Loyalty Program' },
          { id: 'taste', label: '🍷 Taste Profiles' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setCustomerTab(tab.id as any)}
            className={`px-4 py-2 rounded-lg font-medium ${
              customerTab === tab.id
                ? 'bg-purple-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {customerTab === 'list' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Customer List */}
          <div className="lg:col-span-2 card">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Customer Directory</h2>
              <button
                onClick={() => setShowNewCustomerModal(true)}
                className="btn btn-primary"
              >
                + New Customer
              </button>
            </div>
            <input
              type="text"
              placeholder="Search by name or phone..."
              value={customerSearch}
              onChange={(e) => setCustomerSearch(e.target.value)}
              className="input mb-4"
            />
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {customers.map(customer => (
                <div
                  key={customer.id}
                  onClick={() => setSelectedCustomer(customer)}
                  className={`p-4 rounded-lg cursor-pointer transition-all ${
                    selectedCustomer?.id === customer.id
                      ? 'bg-purple-100 border-2 border-purple-500'
                      : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium">{customer.name}</p>
                      <p className="text-sm text-gray-600">{customer.phone}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-purple-600 font-bold">{customer.loyalty_points} pts</p>
                      <p className="text-sm text-gray-500">{formatCurrency(customer.total_spent)} spent</p>
                    </div>
                  </div>
                </div>
              ))}
              {customers.length === 0 && (
                <p className="text-center text-gray-500 py-8">No customers found</p>
              )}
            </div>
          </div>

          {/* Customer Details */}
          <div className="card">
            <h2 className="text-xl font-bold mb-4">Customer Details</h2>
            {selectedCustomer ? (
              <div className="space-y-4">
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="w-20 h-20 bg-purple-200 rounded-full mx-auto flex items-center justify-center text-3xl">
                    {selectedCustomer.name.charAt(0).toUpperCase()}
                  </div>
                  <h3 className="text-xl font-bold mt-3">{selectedCustomer.name}</h3>
                  <p className="text-gray-600">{selectedCustomer.phone}</p>
                  {selectedCustomer.email && (
                    <p className="text-gray-500 text-sm">{selectedCustomer.email}</p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-gray-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-purple-600">{selectedCustomer.loyalty_points}</p>
                    <p className="text-sm text-gray-600">Loyalty Points</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-green-600">{formatCurrency(selectedCustomer.total_spent)}</p>
                    <p className="text-sm text-gray-600">Total Spent</p>
                  </div>
                </div>

                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">Member Since</p>
                  <p className="font-medium">{formatDate(selectedCustomer.join_date)}</p>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setSelectedCustomer(selectedCustomer)
                      setView('pos')
                    }}
                    className="flex-1 btn btn-primary"
                  >
                    Start Sale
                  </button>
                  <button className="btn btn-secondary">Edit</button>
                </div>
              </div>
            ) : (
              <p className="text-center text-gray-500 py-8">Select a customer to view details</p>
            )}
          </div>
        </div>
      )}

      {customerTab === 'loyalty' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="card bg-gradient-to-br from-purple-500 to-purple-700 text-white">
            <h3 className="text-xl font-bold mb-2">🏆 Loyalty Program</h3>
            <p className="text-purple-200 mb-4">Customers earn 1 point per $1 spent</p>
            <div className="space-y-3">
              <div className="bg-white/20 rounded-lg p-3">
                <p className="font-bold">🥉 Bronze</p>
                <p className="text-sm">0-499 points • 5% off</p>
              </div>
              <div className="bg-white/20 rounded-lg p-3">
                <p className="font-bold">🥈 Silver</p>
                <p className="text-sm">500-999 points • 10% off</p>
              </div>
              <div className="bg-white/20 rounded-lg p-3">
                <p className="font-bold">🥇 Gold</p>
                <p className="text-sm">1000+ points • 15% off</p>
              </div>
            </div>
          </div>

          <div className="card col-span-1 md:col-span-2">
            <h3 className="text-xl font-bold mb-4">🌟 Top Loyalty Members</h3>
            <div className="space-y-3">
              {customers.sort((a, b) => b.loyalty_points - a.loyalty_points).slice(0, 5).map((customer, i) => (
                <div key={customer.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '⭐'}</span>
                    <div>
                      <p className="font-medium">{customer.name}</p>
                      <p className="text-sm text-gray-600">{customer.phone}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-bold text-purple-600">{customer.loyalty_points}</p>
                    <p className="text-sm text-gray-500">points</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {customerTab === 'taste' && (
        <div className="card">
          <h3 className="text-xl font-bold mb-4">🍷 Customer Taste Profiles</h3>
          <p className="text-gray-600 mb-6">
            Track customer preferences to provide personalized recommendations
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {customers.slice(0, 6).map(customer => (
              <div key={customer.id} className="p-4 border rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-purple-200 rounded-full flex items-center justify-center">
                    {customer.name.charAt(0)}
                  </div>
                  <div>
                    <p className="font-medium">{customer.name}</p>
                  </div>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex gap-1 flex-wrap">
                    <span className="px-2 py-1 bg-red-100 text-red-700 rounded">Red Wine</span>
                    <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded">Whiskey</span>
                    <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded">IPA</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  // Reports View
  const ReportsView = () => (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Period Selector */}
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-xl font-bold">📈 Sales Reports</h2>
          <div className="flex gap-2">
            {[
              { id: 'today', label: 'Today' },
              { id: 'week', label: 'This Week' },
              { id: 'month', label: 'This Month' }
            ].map(period => (
              <button
                key={period.id}
                onClick={() => setReportPeriod(period.id as any)}
                className={`px-4 py-2 rounded-lg font-medium ${
                  reportPeriod === period.id
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {period.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loadingReport ? (
        <div className="card text-center py-12">
          <div className="text-4xl mb-4 animate-spin">⏳</div>
          <p className="text-gray-600">Loading report data...</p>
        </div>
      ) : reportData ? (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card text-center">
              <p className="text-gray-600 mb-1">Total Revenue</p>
              <p className="text-3xl font-bold text-green-600">{formatCurrency(reportData.total_sales)}</p>
            </div>
            <div className="card text-center">
              <p className="text-gray-600 mb-1">Transactions</p>
              <p className="text-3xl font-bold text-blue-600">{reportData.total_transactions}</p>
            </div>
            <div className="card text-center">
              <p className="text-gray-600 mb-1">Avg. Transaction</p>
              <p className="text-3xl font-bold text-purple-600">{formatCurrency(reportData.average_transaction)}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Products */}
            <div className="card">
              <h3 className="text-xl font-bold mb-4">🏆 Top Products</h3>
              <div className="space-y-3">
                {reportData.top_products.map((product, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}</span>
                      <div>
                        <p className="font-medium">{product.name}</p>
                        <p className="text-sm text-gray-600">{product.quantity} units</p>
                      </div>
                    </div>
                    <p className="font-bold text-green-600">{formatCurrency(product.revenue)}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Sales by Category */}
            <div className="card">
              <h3 className="text-xl font-bold mb-4">📊 Sales by Category</h3>
              <div className="space-y-3">
                {reportData.sales_by_category.map((cat, i) => {
                  const maxRevenue = Math.max(...reportData.sales_by_category.map(c => c.revenue))
                  const percentage = (cat.revenue / maxRevenue) * 100
                  return (
                    <div key={i}>
                      <div className="flex justify-between mb-1">
                        <span className="font-medium">{cat.category}</span>
                        <span className="text-green-600">{formatCurrency(cat.revenue)}</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-purple-600 rounded-full"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Hourly Sales Chart */}
          <div className="card">
            <h3 className="text-xl font-bold mb-4">⏰ Sales by Hour</h3>
            <div className="flex items-end gap-2 h-48">
              {reportData.sales_by_hour.map((hourData, i) => {
                const maxRevenue = Math.max(...reportData.sales_by_hour.map(h => h.revenue))
                const height = maxRevenue > 0 ? (hourData.revenue / maxRevenue) * 100 : 0
                return (
                  <div key={i} className="flex-1 flex flex-col items-center">
                    <div
                      className="w-full bg-purple-500 rounded-t hover:bg-purple-600 transition-colors"
                      style={{ height: `${height}%`, minHeight: '4px' }}
                      title={formatCurrency(hourData.revenue)}
                    />
                    <span className="text-xs text-gray-500 mt-1">{hourData.hour}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </>
      ) : (
        <div className="card text-center py-12">
          <div className="text-4xl mb-4">📊</div>
          <p className="text-gray-600">No report data available</p>
        </div>
      )}
    </div>
  )

  // Delivery View
  const DeliveryView = () => (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Delivery Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Pending', count: deliveryOrders.filter(d => d.status === 'pending').length, color: 'yellow', icon: '📋' },
          { label: 'Assigned', count: deliveryOrders.filter(d => d.status === 'assigned').length, color: 'blue', icon: '👤' },
          { label: 'Out for Delivery', count: deliveryOrders.filter(d => d.status === 'out_for_delivery').length, color: 'purple', icon: '🚗' },
          { label: 'Delivered Today', count: deliveryOrders.filter(d => d.status === 'delivered').length, color: 'green', icon: '✅' }
        ].map(stat => (
          <div key={stat.label} className={`card bg-${stat.color}-50 border-l-4 border-${stat.color}-500`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{stat.label}</p>
                <p className="text-2xl font-bold">{stat.count}</p>
              </div>
              <span className="text-3xl">{stat.icon}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'pending', 'assigned', 'out_for_delivery', 'delivered'].map(status => (
          <button
            key={status}
            onClick={() => setDeliveryFilter(status)}
            className={`px-4 py-2 rounded-lg font-medium capitalize ${
              deliveryFilter === status
                ? 'bg-purple-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {status.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Delivery Orders List */}
      <div className="card">
        <h2 className="text-xl font-bold mb-4">🚗 Delivery Orders</h2>
        <div className="space-y-4">
          {deliveryOrders
            .filter(d => deliveryFilter === 'all' || d.status === deliveryFilter)
            .map(delivery => (
            <div key={delivery.id} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
              <div className="flex flex-wrap justify-between items-start gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-bold text-lg">Order #{delivery.sale_id}</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      delivery.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                      delivery.status === 'assigned' ? 'bg-blue-100 text-blue-700' :
                      delivery.status === 'out_for_delivery' ? 'bg-purple-100 text-purple-700' :
                      delivery.status === 'delivered' ? 'bg-green-100 text-green-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {delivery.status.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="font-medium">{delivery.customer_name}</p>
                  <p className="text-gray-600">{delivery.address}</p>
                  <p className="text-gray-500 text-sm">{delivery.phone}</p>
                  {delivery.delivery_notes && (
                    <p className="text-sm text-purple-600 mt-1">📝 {delivery.delivery_notes}</p>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500">Scheduled</p>
                  <p className="font-medium">{formatDateTime(delivery.scheduled_time)}</p>
                  {delivery.driver_name && (
                    <p className="text-sm text-blue-600 mt-2">🚗 {delivery.driver_name}</p>
                  )}
                </div>
              </div>
              {delivery.status !== 'delivered' && delivery.status !== 'cancelled' && (
                <div className="flex gap-2 mt-4 pt-4 border-t">
                  {delivery.status === 'pending' && (
                    <button
                      onClick={() => updateDeliveryStatus(delivery.id, 'assigned')}
                      className="btn bg-blue-100 text-blue-700 hover:bg-blue-200"
                    >
                      Assign Driver
                    </button>
                  )}
                  {delivery.status === 'assigned' && (
                    <button
                      onClick={() => updateDeliveryStatus(delivery.id, 'out_for_delivery')}
                      className="btn bg-purple-100 text-purple-700 hover:bg-purple-200"
                    >
                      Mark Out for Delivery
                    </button>
                  )}
                  {delivery.status === 'out_for_delivery' && (
                    <button
                      onClick={() => updateDeliveryStatus(delivery.id, 'delivered')}
                      className="btn bg-green-100 text-green-700 hover:bg-green-200"
                    >
                      Mark Delivered
                    </button>
                  )}
                  <button
                    onClick={() => updateDeliveryStatus(delivery.id, 'cancelled')}
                    className="btn bg-red-100 text-red-700 hover:bg-red-200"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          ))}
          {deliveryOrders.length === 0 && (
            <p className="text-center text-gray-500 py-8">No delivery orders</p>
          )}
        </div>
      </div>
    </div>
  )

  // Events View
  const EventsView = () => (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">🍷 Tasting Events & Wine Flights</h2>
        <button
          onClick={() => setShowEventModal(true)}
          className="btn btn-primary"
        >
          + Create Event
        </button>
      </div>

      {/* Upcoming Events */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {tastingEvents.map(event => (
          <div key={event.id} className="card hover:shadow-xl transition-shadow">
            <div className="flex justify-between items-start mb-4">
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                event.status === 'scheduled' ? 'bg-green-100 text-green-700' :
                event.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {event.status}
              </span>
              <span className="text-2xl">🍷</span>
            </div>
            <h3 className="text-xl font-bold mb-2">{event.name}</h3>
            <p className="text-gray-600 text-sm mb-4">{event.description}</p>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span>📅</span>
                <span>{formatDate(event.event_date)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span>⏰</span>
                <span>{formatTime(event.start_time)} - {formatTime(event.end_time)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span>👥</span>
                <span>{event.current_attendees} / {event.max_attendees} spots</span>
              </div>
              <div className="flex items-center gap-2">
                <span>💰</span>
                <span className="font-bold text-purple-600">{formatCurrency(event.price_per_person)} per person</span>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t">
              <div className="flex justify-between items-center">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-purple-600 h-2 rounded-full"
                    style={{ width: `${(event.current_attendees / event.max_attendees) * 100}%` }}
                  />
                </div>
              </div>
              <button className="w-full btn btn-primary mt-3">
                Manage Event
              </button>
            </div>
          </div>
        ))}
        {tastingEvents.length === 0 && (
          <div className="col-span-full card text-center py-12">
            <div className="text-5xl mb-4">🍷</div>
            <p className="text-gray-600">No events scheduled</p>
            <button
              onClick={() => setShowEventModal(true)}
              className="btn btn-primary mt-4"
            >
              Create Your First Event
            </button>
          </div>
        )}
      </div>

      {/* Wine Flight Builder */}
      <div className="card">
        <h3 className="text-xl font-bold mb-4">✨ Wine Flight Builder</h3>
        <p className="text-gray-600 mb-4">Create curated wine flights for tastings</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 border-2 border-dashed border-gray-300 rounded-lg text-center hover:border-purple-500 cursor-pointer transition-colors">
            <span className="text-3xl">🍷</span>
            <p className="font-medium mt-2">Red Wine Flight</p>
            <p className="text-sm text-gray-500">3-5 wines</p>
          </div>
          <div className="p-4 border-2 border-dashed border-gray-300 rounded-lg text-center hover:border-purple-500 cursor-pointer transition-colors">
            <span className="text-3xl">🥂</span>
            <p className="font-medium mt-2">White & Rosé Flight</p>
            <p className="text-sm text-gray-500">3-5 wines</p>
          </div>
          <div className="p-4 border-2 border-dashed border-gray-300 rounded-lg text-center hover:border-purple-500 cursor-pointer transition-colors">
            <span className="text-3xl">🥃</span>
            <p className="font-medium mt-2">Spirits Flight</p>
            <p className="text-sm text-gray-500">3-4 spirits</p>
          </div>
        </div>
      </div>
    </div>
  )

  // Settings View
  const SettingsView = () => (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Settings Tabs */}
      <div className="flex gap-2 flex-wrap">
        {[
          { id: 'store', label: '🏪 Store Info' },
          { id: 'employees', label: '👥 Employees' },
          { id: 'happyhour', label: '🎉 Happy Hour' },
          { id: 'seasonal', label: '🎄 Seasonal Promos' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setSettingsTab(tab.id as any)}
            className={`px-4 py-2 rounded-lg font-medium ${
              settingsTab === tab.id
                ? 'bg-purple-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {settingsTab === 'store' && (
        <div className="card">
          <h2 className="text-xl font-bold mb-6">Store Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Store Name</label>
              <input
                type="text"
                value={storeSettings.name}
                onChange={(e) => setStoreSettings({...storeSettings, name: e.target.value})}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
              <input
                type="text"
                value={storeSettings.phone}
                onChange={(e) => setStoreSettings({...storeSettings, phone: e.target.value})}
                className="input"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
              <input
                type="text"
                value={storeSettings.address}
                onChange={(e) => setStoreSettings({...storeSettings, address: e.target.value})}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Opening Time</label>
              <input
                type="time"
                value={storeSettings.opening_time}
                onChange={(e) => setStoreSettings({...storeSettings, opening_time: e.target.value})}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Closing Time</label>
              <input
                type="time"
                value={storeSettings.closing_time}
                onChange={(e) => setStoreSettings({...storeSettings, closing_time: e.target.value})}
                className="input"
              />
            </div>
          </div>
          <button className="btn btn-primary mt-6">Save Changes</button>
        </div>
      )}

      {settingsTab === 'employees' && (
        <div className="card">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold">Employee Management</h2>
            <button className="btn btn-primary">+ Add Employee</button>
          </div>
          <div className="space-y-4">
            {employees.map((emp: any) => (
              <div key={emp.id} className="flex justify-between items-center p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-purple-200 rounded-full flex items-center justify-center text-xl">
                    {emp.name?.charAt(0) || '?'}
                  </div>
                  <div>
                    <p className="font-medium">{emp.name}</p>
                    <p className="text-sm text-gray-600">{emp.role}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs ${
                    emp.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {emp.status}
                  </span>
                  <button className="btn btn-secondary text-sm">Edit</button>
                </div>
              </div>
            ))}
            {employees.length === 0 && (
              <p className="text-center text-gray-500 py-8">No employees configured</p>
            )}
          </div>
        </div>
      )}

      {settingsTab === 'happyhour' && (
        <div className="card">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold">🎉 Happy Hour Settings</h2>
            <button className="btn btn-primary">+ Add Happy Hour</button>
          </div>
          <div className="space-y-4">
            {happyHours.map(hh => (
              <div key={hh.id} className="p-4 border rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-bold text-lg">{hh.name}</h3>
                    <p className="text-gray-600">
                      {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][hh.day_of_week]} • {formatTime(hh.start_time)} - {formatTime(hh.end_time)}
                    </p>
                    <p className="text-green-600 font-medium mt-1">{hh.discount_percent}% off</p>
                  </div>
                  <span className={`px-2 py-1 rounded text-sm ${
                    hh.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {hh.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            ))}
            {happyHours.length === 0 && (
              <p className="text-center text-gray-500 py-8">No happy hours configured</p>
            )}
          </div>
        </div>
      )}

      {settingsTab === 'seasonal' && (
        <div className="card">
          <h2 className="text-xl font-bold mb-6">🎄 Seasonal Promotions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-3xl">🎄</span>
                <div>
                  <h3 className="font-bold">Holiday Wine Special</h3>
                  <p className="text-sm text-gray-600">Dec 1 - Dec 31</p>
                </div>
              </div>
              <p className="text-green-600 font-medium">20% off select wines</p>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-3xl">🏈</span>
                <div>
                  <h3 className="font-bold">Super Bowl Party Pack</h3>
                  <p className="text-sm text-gray-600">Feb 1 - Game Day</p>
                </div>
              </div>
              <p className="text-green-600 font-medium">Buy 2 cases, get 10% off</p>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-3xl">☀️</span>
                <div>
                  <h3 className="font-bold">Summer Sippers</h3>
                  <p className="text-sm text-gray-600">Jun 1 - Aug 31</p>
                </div>
              </div>
              <p className="text-green-600 font-medium">15% off rosé & seltzers</p>
            </div>
            <div className="p-4 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center cursor-pointer hover:border-purple-500">
              <span className="text-gray-500">+ Add Seasonal Promotion</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  // Inventory View
  const InventoryView = () => (
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
            <div className="space-y-3 max-h-96 overflow-y-auto">
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
                    <span>{formatCurrency(totalValue)} value</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Quick Reorder */}
        <div className="card md:col-span-2">
          <h2 className="text-xl font-bold mb-4">📦 Quick Reorder</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {lowStockAlert.slice(0, 4).map((product: any) => (
              <div key={product.id} className="p-4 border rounded-lg">
                <p className="font-medium">{product.name}</p>
                <p className="text-sm text-gray-600">{product.brand}</p>
                <div className="mt-3 flex gap-2">
                  <input
                    type="number"
                    defaultValue={product.case_size || 12}
                    className="input flex-1 text-center"
                    min={1}
                  />
                  <button className="btn btn-primary">Order</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )

  // POS View
  const POSView = () => (
    <div className="max-w-7xl mx-auto px-4 py-6 flex gap-6">
      {/* Products Section */}
      <div className="flex-1">
        {/* Customer Selection */}
        {selectedCustomer && (
          <div className="mb-4 p-4 bg-purple-50 rounded-lg flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-200 rounded-full flex items-center justify-center">
                {selectedCustomer.name.charAt(0)}
              </div>
              <div>
                <p className="font-medium">{selectedCustomer.name}</p>
                <p className="text-sm text-purple-600">{selectedCustomer.loyalty_points} points</p>
              </div>
            </div>
            <button
              onClick={() => setSelectedCustomer(null)}
              className="text-purple-600 hover:text-purple-800"
            >
              ✕ Remove
            </button>
          </div>
        )}

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
                  {product.name} - {formatCurrency(product.price)}
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
              {product.abv && (
                <p className="text-xs text-gray-500">{product.abv}% ABV</p>
              )}
              <div className="mt-2 flex justify-between items-end">
                <div>
                  <span className="text-lg font-bold text-purple-600">
                    {formatCurrency(product.price)}
                  </span>
                  {product.case_price && (
                    <span className="text-xs text-gray-500 block">
                      Case ({product.case_size}): {formatCurrency(product.case_price)}
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
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {cart.map(item => (
                <div key={item.product.id} className="cart-item">
                  <div className="flex-1">
                    <p className="font-medium">{item.product.name}</p>
                    <p className="text-sm text-gray-500">
                      {formatCurrency(item.product.price)} each
                      {item.product.case_price && item.quantity >= item.product.case_size && (
                        <span className="text-green-600 ml-1">(Case pricing!)</span>
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

            {/* Gift Card */}
            {appliedGiftCard ? (
              <div className="mt-4 p-3 bg-green-50 rounded-lg flex justify-between items-center">
                <div>
                  <p className="text-sm font-medium text-green-700">🎁 Gift Card Applied</p>
                  <p className="text-xs text-green-600">-{formatCurrency(calculateGiftCardDiscount())}</p>
                </div>
                <button
                  onClick={() => setAppliedGiftCard(null)}
                  className="text-green-600 hover:text-green-800"
                >
                  Remove
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowGiftCardModal(true)}
                className="w-full mt-4 btn btn-secondary"
              >
                🎁 Apply Gift Card
              </button>
            )}

            <div className="border-t mt-4 pt-4 space-y-2">
              <div className="flex justify-between text-gray-600">
                <span>Subtotal</span>
                <span>{formatCurrency(calculateSubtotal())}</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>Tax</span>
                <span>{formatCurrency(calculateTax())}</span>
              </div>
              {appliedGiftCard && (
                <div className="flex justify-between text-green-600">
                  <span>Gift Card</span>
                  <span>-{formatCurrency(calculateGiftCardDiscount())}</span>
                </div>
              )}
              <div className="flex justify-between text-xl font-bold">
                <span>Total</span>
                <span>{formatCurrency(calculateTotal())}</span>
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
  )

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-purple-700 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold">🍷 Craft & Cork Liquor</h1>
            {ageVerified && (
              <span className="bg-green-500 text-white text-xs px-2 py-1 rounded-full">
                21+ Verified
              </span>
            )}
            {dashboardStats.activeHappyHour && (
              <span className="bg-yellow-500 text-white text-xs px-2 py-1 rounded-full animate-pulse">
                🎉 Happy Hour!
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            {currentShift && (
              <span className="text-purple-200 text-sm">
                Shift: {formatTime(currentShift.start_time.split('T')[1]?.slice(0, 5) || '00:00')}
              </span>
            )}
            <button
              onClick={() => setAgeVerified(!ageVerified)}
              className={`btn ${ageVerified ? 'bg-green-500' : 'bg-purple-600'}`}
            >
              {ageVerified ? '✓ 21+ Mode' : '21+ Verify'}
            </button>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      {view === 'pos' && <POSView />}
      {view === 'dashboard' && <DashboardView />}
      {view === 'customers' && <CustomersView />}
      {view === 'inventory' && <InventoryView />}
      {view === 'reports' && <ReportsView />}
      {view === 'delivery' && <DeliveryView />}
      {view === 'events' && <EventsView />}
      {view === 'settings' && <SettingsView />}

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
                <button onClick={() => setShowAgeModal(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button onClick={confirmAge} className="btn btn-primary">
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
                {formatCurrency(calculateTotal())}
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

      {/* Gift Card Modal */}
      {showGiftCardModal && (
        <div className="modal-backdrop" onClick={() => setShowGiftCardModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">🎁 Gift Card</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Enter Gift Card Code</label>
                <input
                  type="text"
                  value={giftCardCode}
                  onChange={(e) => setGiftCardCode(e.target.value.toUpperCase())}
                  placeholder="XXXX-XXXX-XXXX"
                  className="input text-center text-lg tracking-widest"
                />
              </div>
              <button onClick={applyGiftCard} className="w-full btn btn-primary">
                Apply Gift Card
              </button>
              <hr />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Or Create New Gift Card</label>
                <div className="flex gap-2">
                  {[25, 50, 100].map(amount => (
                    <button
                      key={amount}
                      onClick={() => setGiftCardAmount(amount)}
                      className={`flex-1 py-2 rounded ${giftCardAmount === amount ? 'bg-purple-600 text-white' : 'bg-gray-100'}`}
                    >
                      ${amount}
                    </button>
                  ))}
                </div>
                <button onClick={createGiftCard} className="w-full btn btn-secondary mt-3">
                  Create {formatCurrency(giftCardAmount)} Gift Card
                </button>
              </div>
            </div>
            <button
              onClick={() => setShowGiftCardModal(false)}
              className="w-full btn btn-secondary mt-4"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* New Customer Modal */}
      {showNewCustomerModal && (
        <div className="modal-backdrop" onClick={() => setShowNewCustomerModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">👤 New Customer</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  type="text"
                  value={newCustomer.name}
                  onChange={(e) => setNewCustomer({...newCustomer, name: e.target.value})}
                  className="input"
                  placeholder="John Smith"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone *</label>
                <input
                  type="tel"
                  value={newCustomer.phone}
                  onChange={(e) => setNewCustomer({...newCustomer, phone: e.target.value})}
                  className="input"
                  placeholder="(555) 123-4567"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={newCustomer.email}
                  onChange={(e) => setNewCustomer({...newCustomer, email: e.target.value})}
                  className="input"
                  placeholder="john@example.com"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowNewCustomerModal(false)} className="flex-1 btn btn-secondary">
                Cancel
              </button>
              <button onClick={createCustomer} className="flex-1 btn btn-primary">
                Create Customer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Event Modal */}
      {showEventModal && (
        <div className="modal-backdrop" onClick={() => setShowEventModal(false)}>
          <div className="modal-content max-w-lg" onClick={e => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">🍷 Create Tasting Event</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Event Name</label>
                <input
                  type="text"
                  value={newEvent.name}
                  onChange={(e) => setNewEvent({...newEvent, name: e.target.value})}
                  className="input"
                  placeholder="Summer Wine Tasting"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={newEvent.description}
                  onChange={(e) => setNewEvent({...newEvent, description: e.target.value})}
                  className="input"
                  rows={3}
                  placeholder="Join us for a selection of summer wines..."
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                  <input
                    type="date"
                    value={newEvent.event_date}
                    onChange={(e) => setNewEvent({...newEvent, event_date: e.target.value})}
                    className="input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Price/Person</label>
                  <input
                    type="number"
                    value={newEvent.price_per_person}
                    onChange={(e) => setNewEvent({...newEvent, price_per_person: parseInt(e.target.value)})}
                    className="input"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
                  <input
                    type="time"
                    value={newEvent.start_time}
                    onChange={(e) => setNewEvent({...newEvent, start_time: e.target.value})}
                    className="input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Time</label>
                  <input
                    type="time"
                    value={newEvent.end_time}
                    onChange={(e) => setNewEvent({...newEvent, end_time: e.target.value})}
                    className="input"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Attendees</label>
                <input
                  type="number"
                  value={newEvent.max_attendees}
                  onChange={(e) => setNewEvent({...newEvent, max_attendees: parseInt(e.target.value)})}
                  className="input"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowEventModal(false)} className="flex-1 btn btn-secondary">
                Cancel
              </button>
              <button onClick={createTastingEvent} className="flex-1 btn btn-primary">
                Create Event
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cash Drawer Modal */}
      {showCashDrawerModal && (
        <div className="modal-backdrop" onClick={() => setShowCashDrawerModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">💵 Cash Drawer</h2>
            {cashDrawer?.status === 'open' ? (
              <div className="space-y-4">
                <div className="p-4 bg-green-50 rounded-lg text-center">
                  <p className="text-sm text-gray-600">Current Amount</p>
                  <p className="text-3xl font-bold text-green-600">{formatCurrency(cashDrawer.current_amount)}</p>
                </div>
                <div className="grid grid-cols-2 gap-4 text-center">
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Opening</p>
                    <p className="font-bold">{formatCurrency(cashDrawer.opening_amount)}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Expected</p>
                    <p className="font-bold">{formatCurrency(cashDrawer.expected_amount)}</p>
                  </div>
                </div>
                <button onClick={closeCashDrawer} className="w-full btn btn-danger">
                  Close Drawer
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-gray-600">Enter opening cash amount:</p>
                <div className="flex gap-2">
                  {[100, 150, 200, 250].map(amount => (
                    <button
                      key={amount}
                      onClick={() => setDrawerAmount(amount)}
                      className={`flex-1 py-2 rounded ${drawerAmount === amount ? 'bg-purple-600 text-white' : 'bg-gray-100'}`}
                    >
                      ${amount}
                    </button>
                  ))}
                </div>
                <input
                  type="number"
                  value={drawerAmount}
                  onChange={(e) => setDrawerAmount(parseInt(e.target.value))}
                  className="input text-center text-xl"
                />
                <button onClick={openCashDrawer} className="w-full btn btn-primary">
                  Open Drawer with {formatCurrency(drawerAmount)}
                </button>
              </div>
            )}
            <button
              onClick={() => setShowCashDrawerModal(false)}
              className="w-full btn btn-secondary mt-4"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Shift Modal */}
      {showShiftModal && (
        <div className="modal-backdrop" onClick={() => setShowShiftModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">⏱️ Shift Management</h2>
            {currentShift ? (
              <div className="space-y-4">
                <div className="p-4 bg-green-50 rounded-lg">
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-sm text-gray-600">Current Shift</p>
                      <p className="font-bold">{currentShift.employee_name}</p>
                    </div>
                    <span className="bg-green-500 text-white px-3 py-1 rounded-full text-sm">Active</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-gray-50 rounded-lg text-center">
                    <p className="text-sm text-gray-600">Started</p>
                    <p className="font-bold">{formatDateTime(currentShift.start_time)}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg text-center">
                    <p className="text-sm text-gray-600">Sales</p>
                    <p className="font-bold text-green-600">{formatCurrency(currentShift.total_sales)}</p>
                  </div>
                </div>
                <button onClick={endShift} className="w-full btn btn-danger">
                  End Shift
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-gray-600 text-center py-4">No active shift</p>
                <button onClick={startShift} className="w-full btn btn-primary">
                  Start New Shift
                </button>
              </div>
            )}
            <button
              onClick={() => setShowShiftModal(false)}
              className="w-full btn btn-secondary mt-4"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Return Modal */}
      {showReturnModal && (
        <div className="modal-backdrop" onClick={() => setShowReturnModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">↩️ Process Return</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sale ID / Receipt Number</label>
                <input
                  type="text"
                  value={returnSaleId}
                  onChange={(e) => setReturnSaleId(e.target.value)}
                  className="input"
                  placeholder="Enter sale ID"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason for Return</label>
                <select
                  value={returnReason}
                  onChange={(e) => setReturnReason(e.target.value)}
                  className="input"
                >
                  <option value="">Select reason...</option>
                  <option value="defective">Defective Product</option>
                  <option value="wrong_item">Wrong Item</option>
                  <option value="customer_changed_mind">Customer Changed Mind</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowReturnModal(false)} className="flex-1 btn btn-secondary">
                Cancel
              </button>
              <button onClick={processReturn} className="flex-1 btn btn-danger">
                Process Return
              </button>
            </div>
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
                Sale #{recentSale.id} • {formatCurrency(recentSale.total)}
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

      {/* Toast Notification */}
      {toast && (
        <div className={`fixed top-20 right-6 rounded-lg shadow-lg p-4 max-w-sm animate-pulse ${
          toast.type === 'success' ? 'bg-green-500 text-white' :
          toast.type === 'error' ? 'bg-red-500 text-white' :
          'bg-blue-500 text-white'
        }`}>
          <p>{toast.message}</p>
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
