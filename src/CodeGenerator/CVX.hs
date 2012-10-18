module CodeGenerator.CVX (cvxgen) where
  import CodeGenerator.Common
    
{-- what follows is for displaying cvx code --}
  cvxgen :: Problem -> Int -> String
  cvxgen EmptyProblem _ = "0";
  cvxgen x c = let problemSense = case(c >= 0) of
                    True -> "minimize "
                    False -> "maximize "
    in unlines $ ["cvx_begin",
      "variables " ++ (unwords $ getVariables x),
      problemSense ++ objLabel x] ++
      getRowConstraints x ++
      getConeConstraints x ++
      [ "cvx_end",
        "ecos_optval = cvx_optval;"]
        
  -- gets the variables (and their sizes) from the problem
  getVariables :: Problem -> [String]
  getVariables p = 
    let extractInfo var = label var ++ "(" ++ (show $ rows var) ++ ")" 
    in map extractInfo (getVariableInfo p)
    
  -- gets string representation of coeff
  getCoeffString :: Coeff -> String
  getCoeffString x = let (m,n,s) = getCoeffInfo x
    in s
  
  -- converts the row constraints in to a string for CVX
  getRowConstraints :: Problem -> [String]
  getRowConstraints p =
    let coeffStrings = map getCoeffString (vectorB p)
    in produceEqConstr coeffStrings (map convertRow (matrixA p))

  -- adds coefficient for multiply on each row
  convertRow :: Row -> ([String],Bool)
  convertRow row = let rowHeights = map (getCoeffRows.snd) (tail row)
                       rowTotal = (getCoeffRows.snd) (head row)
                       isConcat = not $ all (==rowTotal) rowHeights
    in (map (\(variable, multiplier) -> let (m,n,s) = getCoeffInfo multiplier
      in s ++ "*" ++ (label variable)) row, isConcat)

  -- produces an equality constraint
  produceEqConstr :: [String]->[([String],Bool)]->[String]
  produceEqConstr b ax = 
    let zipFunc x y = x ++ " == " ++ y
    in zipWith zipFunc (flattenEqConstr ax) b

  -- flattens the lhs of each row by adding "+"
  flattenEqConstr :: [([String],Bool)] -> [String]
  flattenEqConstr [([],_)] = [""] 
  flattenEqConstr ax = let axs = map fst ax
                           concats = map snd ax
                      in zipWith emitConstraint concats axs

  -- emits a row of the equality constraints
  emitConstraint :: Bool -> [String] -> String
  emitConstraint False x = intercalate " + " x
  emitConstraint True x 
    = (head x) ++ " + " ++ "["++(intercalate "; " (tail x)) ++"]"

  -- gets the cone constraints
  getConeConstraints :: Problem -> [String]
  getConeConstraints p = map convertCone (conesK p)

  -- converts cone constraints to CVX string
  convertCone :: SOC -> String
  convertCone (SOC vars) = case (length vars) of
    1 -> (label $ head vars) ++ " >= 0"
    otherwise -> "norm([" ++ (intercalate ", " (map label (tail vars))) ++ "]) <= " ++ (label $ head vars)
  convertCone (SOCelem vars) = case (length vars) of
    1 -> (label $ head vars) ++ " >= 0"
    otherwise -> "norms([" ++ (intercalate ", " (map label (tail vars))) ++ "]')' <= " ++ (label $ head vars)